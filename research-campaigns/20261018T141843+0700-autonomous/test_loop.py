"""Deterministic orchestration checks, no model call or competition execution."""
import contextlib,io,json,sys,tempfile,unittest
from pathlib import Path
import loop,make_fresh,release
from unittest.mock import patch
class Tests(unittest.TestCase):
    def test_patch_unique(self):
        p='int main(){return 0;}'
        r=dict(full_source='',changes=[dict(find='return 0;',replace='return 1;')])
        with self.assertRaisesRegex(ValueError,'length'):loop.apply(p,r)
        p='//'+('x'*300)+'\n'+p
        self.assertIn('return 1;',loop.apply(p,r))
        r['changes'][0]['find']='absent'
        with self.assertRaisesRegex(ValueError,'exactly once'):loop.apply(p,r)
    def test_external_rejected(self):
        p='//'+('x'*300)+'\nint main(){return 0;}'
        with self.assertRaisesRegex(ValueError,'external'):
            loop.apply(p,dict(full_source=p+'\nvoid bad(){fopen("x","r");}',changes=[]))
    def test_case_selection_by_id(self):
        def row(name,s15,s13):
            return dict(id=name,weighted_score=0,fresh_mean_kpi=0,cases=[dict(case='13',weighted_score=s13),dict(case='15',weighted_score=s15)])
        a=row('a',10,1);b=row('b',9,4)
        self.assertEqual(loop.choose([a,b],5)['id'],'a')
        self.assertEqual(loop.choose([a,b],3)['id'],'b')
    def test_fresh_independent_valid(self):
        rows=make_fresh.design('dev')['cases']+make_fresh.design('release')['cases']
        self.assertEqual(len({r['spec']['seed'] for r in rows}),len(rows))
        for r in rows:
            if r['kind'] not in ['micro','frames']:continue
            ops=make_fresh.custom(r);alive=set();pid=0
            for c in ops:
                if c>0:self.assertLessEqual(c,40);pid+=1;alive.add(pid)
                else:self.assertIn(-c,alive);alive.remove(-c)
            self.assertTrue(alive);self.assertEqual(len(ops),r['spec']['operations'])
    def test_comparison_matches_hash(self):
        a=dict(records=[dict(test_sha256='a',kpi=.5),dict(test_sha256='b',kpi=.8)])
        b=dict(records=[dict(test_sha256='b',kpi=.7),dict(test_sha256='a',kpi=.7)])
        c=loop.compare(a,b);self.assertEqual((c['wins'],c['regressions']),(1,1));self.assertAlmostEqual(c['mean_delta'],-.05)
    def test_no_tools_and_no_api_keys(self):
        cmd=loop.text_command(['exec','--json','--model','gpt-6.1-sol','-'],Path('/tmp'))
        for s in ['features.shell_tool=false','features.code_mode=false','features.multi_agent=false','service_tier="default"','project_doc_max_bytes=0']:
            self.assertIn(s,cmd)
        env=loop.subscription_environment()
        self.assertNotIn('OPENAI_API_KEY',env);self.assertNotIn('CODEX_API_KEY',env)
    def test_compiler_repair_gets_error_and_previous_proposal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'proposals').mkdir();source=root/'parent.cpp';source.write_text('//'+('x'*300)+'\nint main(){return 0;}')
            out=root/'failed_output';out.mkdir();(out/'compile.log').write_text('COMPILER_MARKER: missing symbol TestSymbol')
            parent=dict(id='parent',source=str(source),sha256=loop.digest(source),weighted_score=1,idea='parent',fresh={},cases=[])
            prompts=[];responses=[]
            for n in [1,2]:responses.append(dict(idea='attempt'+str(n),hypothesis='h',causality='c',full_source='',changes=[dict(find='return 0;',replace=f'return {n};')]))
            def model(prompt,out):prompts.append(prompt);return responses[len(prompts)-1]
            results=[dict(status='invalid',manifest=dict(status='compile_failed',compile_command=['c++','-o',str(out/'solver')])),dict(status='completed',weighted_score=2)]
            def record(*a,**kw):return results.pop(0)
            with patch.object(loop,'ROOT',root),patch.object(loop,'model',model),patch.object(loop,'record',record),patch.object(loop,'bump',lambda key:None):
                result=loop.propose(1,parent,[parent])
            self.assertEqual(result['status'],'completed');self.assertEqual(len(prompts),2)
            self.assertIn('COMPILER_MARKER',prompts[1]);self.assertIn('return 1;',prompts[1]);self.assertIn('ORIGINAL parent',prompts[1])
    def test_recovery_does_not_reserve_same_trial_twice(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source.cpp';source.write_text('stable source')
            loop.save(root/'manifest.json',dict(target_evaluated=2));loop.save(root/'counters.json',dict(model_calls=0,evaluated=0,failed_proposals=0))
            with patch.object(loop,'ROOT',root):
                loop.reserve_evaluation(root/'trial',source);loop.reserve_evaluation(root/'trial',source)
                self.assertEqual(json.loads((root/'counters.json').read_text())['evaluation_attempts'],1)
                source.write_text('changed source')
                with self.assertRaisesRegex(RuntimeError,'source changed'):loop.reserve_evaluation(root/'trial',source)
    def test_completed_recovery_output_reused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();source=root/'source.cpp';source.write_text('stable source');tests=root/'inputs';tests.mkdir();test=tests/'a.in';test.write_text('1 1\n1\n0\n')
            out=root/'eval';out.mkdir();recovered=root/'eval_recovery_1';recovered.mkdir();(recovered/'source.cpp').write_bytes(source.read_bytes());s=recovered/'summary.json';s.write_text('{}')
            m=dict(source_sha256=loop.digest(source),tests=str(tests),input_sha256={str(test):loop.digest(test)},status='completed',correct=True,summary_path=str(s),summary_sha256=loop.digest(s))
            loop.save(recovered/'manifest.json',m)
            with patch.object(loop,'evaluate',side_effect=AssertionError('must not rerun evaluator')):
                self.assertEqual(loop.reuse_or_evaluate(source,tests,out,'recovery'),m)
    def test_release_cannot_masquerade_as_new_replication(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();source=root/'source.cpp';source.write_text('frozen source');sha=loop.digest(source);out=root/'releases'/sha;out.mkdir(parents=True)
            result=out/'release-result.json';result.write_text(json.dumps(dict(source_sha256=sha,created_at=123)))
            loop.save(out/'freeze.json',dict(release_results_seen=False));before=loop.digest(result);stdout=io.StringIO()
            with patch.object(release,'ROOT',root),patch.object(release,'quota',lambda:None),patch.object(sys,'argv',['release.py','--source',str(source)]),contextlib.redirect_stdout(stdout):release.main()
            self.assertEqual(loop.digest(result),before);self.assertFalse(json.loads(stdout.getvalue())['new_independent_replication']);self.assertTrue(json.loads((out/'freeze.json').read_text())['release_results_seen'])
if __name__=='__main__':unittest.main()
