import argparse
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import ci_watch
import github_cli
import pr_snapshot

SHA = 'a' * 40


def run(workflow=1, identity=1, status='completed', conclusion='success', **extra):
    return {'workflow_id': workflow, 'id': identity, 'run_attempt': 1, 'head_sha': SHA,
            'head_branch': 'main', 'event': 'push', 'status': status, 'conclusion': conclusion, **extra}


class WatchTests(unittest.TestCase):
    def assess(self, runs, expected=(1,2)):
        return ci_watch.assess(runs, SHA, 'main', 'push', set(expected))[0]

    def test_missing_workflow_not_pass(self):
        self.assertEqual(self.assess([run()]), 'pending')
        self.assertEqual(self.assess([]), 'pending')

    def test_full_set_passes(self):
        self.assertEqual(self.assess([run(), run(2,2)]), 'passed')

    def test_wrong_sha_branch_event_excluded(self):
        for extra in ({'head_sha': SHA+'b'}, {'head_branch':'other'}, {'event':'pull_request'}):
            self.assertEqual(self.assess([run(),run(2,2,**extra)]), 'pending')

    def test_newest_run_and_attempt(self):
        self.assertEqual(self.assess([run(conclusion='failure'),run(identity=3),run(2,2)]), 'passed')
        self.assertEqual(self.assess([run(),run(identity=1,run_attempt=2,status='in_progress',conclusion=None),run(2,2)]), 'pending')

    def test_failure_reported_while_other_workflow_pending(self):
        self.assertEqual(self.assess([run(conclusion='failure'),run(2,2,status='queued',conclusion=None)]), 'failed')

    def test_skipped_neutral_and_unknown_are_not_green(self):
        for conclusion in ('skipped','neutral','cancelled','stale','startup_failure',None):
            self.assertEqual(self.assess([run(conclusion=conclusion),run(2,2)]), 'failed')

    def test_unrelated_workflow_failure_does_not_block_declared_set(self):
        self.assertEqual(self.assess([run(),run(2,2),run(3,3,conclusion='failure')]), 'passed')

    def test_pagination_is_verified(self):
        options=argparse.Namespace(repo='owner/repo', head_sha=SHA, branch='main', event='push')
        with patch.object(ci_watch,'gh_json',return_value=[{'total_count':2,'workflow_runs':[run()]},{'total_count':2,'workflow_runs':[run(2,2)]}]):
            self.assertEqual(len(ci_watch.fetch_runs(options,5)),2)
        for pages in ([{'total_count':2,'workflow_runs':[run()]}],[{'total_count':1000,'workflow_runs':[]}],[]):
            with patch.object(ci_watch,'gh_json',return_value=pages), self.assertRaises(ValueError):
                ci_watch.fetch_runs(options,5)

    def test_cli_rejects_short_sha_and_bounds_api_call(self):
        args=['ci_watch','--repo','o/r','--branch','main','--head-sha','abc','--workflow-id','1']
        with patch.object(sys,'argv',args),contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ci_watch.main(),2)
        args[args.index('abc')]=SHA
        with patch.object(sys,'argv',args),patch.object(ci_watch,'fetch_runs',side_effect=subprocess.TimeoutExpired('gh',1)),contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ci_watch.main(),2)

    def test_nonfinite_deadlines_are_rejected_before_query(self):
        for flag in ('--timeout','--interval'):
            for value in ('nan','inf'):
                args=['ci_watch','--repo','o/r','--branch','main','--head-sha',SHA,'--workflow-id','1',flag,value]
                with patch.object(sys,'argv',args),patch.object(ci_watch,'fetch_runs') as fetch,contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(ci_watch.main(),2)
                    fetch.assert_not_called()


class SnapshotTests(unittest.TestCase):
    def options(self):return argparse.Namespace(authmux=False,context=None)

    def test_queue_cap_probes_one_extra(self):
        with patch.object(pr_snapshot,'gh_json',side_effect=[[{'number':1},{'number':2}],{'body':'one'}]) as call:
            prs,truncated=pr_snapshot.fetch_prs('open',1,'o/r',self.options())
            self.assertTrue(truncated)
            self.assertEqual(len(prs),1)
            self.assertIn('2',call.call_args_list[0].args[0])

    def test_detail_failure_is_retained(self):
        with patch.object(pr_snapshot,'gh_json',side_effect=[[{'number':1}],RuntimeError('unavailable')]):
            prs,_=pr_snapshot.fetch_prs('open',3,'o/r',self.options())
            self.assertEqual(prs[0]['viewError'],'unavailable')

    def test_legacy_status_and_file_coverage(self):
        prs=pr_snapshot.normalize([{'changedFiles':2,'files':[{'path':'a'}],'headRefOid':SHA,
                                    'statusCheckRollup':[{'context':'external-ci','state':'FAILURE'}]}],100)
        self.assertTrue(prs[0]['filesIncomplete'])
        self.assertEqual(prs[0]['checks'][0]['status'],'FAILURE')
        self.assertEqual(prs[0]['checks'][0]['name'],'external-ci')
        self.assertEqual(prs[0]['headSha'],SHA)

    def test_cli_partial_exit_and_json_envelope(self):
        args=['pr_snapshot','--format','json']
        output=io.StringIO()
        with patch.object(sys,'argv',args),patch.object(pr_snapshot,'fetch_prs',return_value=([{'number':1}],True)),contextlib.redirect_stdout(output):
            self.assertEqual(pr_snapshot.main(),2)
        self.assertTrue(json.loads(output.getvalue())['coverage']['queue_truncated'])

    def test_auth_failure_stops_remaining_details(self):
        failure=github_cli.CliError(10, 'reauthentication event', ['authmux','exec','--','gh','pr','view','1'])
        with patch.object(pr_snapshot,'gh_json',side_effect=[[{'number':1},{'number':2}],failure]) as fetch:
            with self.assertRaises(github_cli.CliError):
                pr_snapshot.fetch_prs('open',3,'o/r',self.options())
            self.assertEqual(fetch.call_count,2)

    def test_markdown_contains_revision_and_coverage(self):
        prs=pr_snapshot.normalize([{'headRefOid':SHA,'baseRefOid':'b'*40,'changedFiles':2,'files':[]}],100)
        output=io.StringIO()
        with contextlib.redirect_stdout(output):pr_snapshot.print_markdown(prs)
        self.assertIn(SHA,output.getvalue())
        self.assertIn('Files incomplete: True',output.getvalue())


class AuthTests(unittest.TestCase):
    def test_guard_preserves_leaf_argv(self):
        options=argparse.Namespace(authmux=True,context='approved')
        with patch.object(github_cli.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'[]','')) as call:
            self.assertEqual(github_cli.gh_json(['pr','list'],options),[])
            self.assertEqual(call.call_args.args[0],['authmux','exec','--context','approved','--','gh','pr','list'])

    def test_auth_failure_is_not_retried(self):
        options=argparse.Namespace(authmux=True,context=None)
        with patch.object(github_cli.subprocess,'run',return_value=subprocess.CompletedProcess([],10,'','reauthentication required')) as call:
            with self.assertRaises(RuntimeError):github_cli.gh_json(['pr','list'],options)
            self.assertEqual(call.call_count,1)


if __name__=='__main__':unittest.main()
