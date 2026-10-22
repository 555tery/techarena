import sys,json
sys.dont_write_bytecode=True
sys.path.insert(0,'/tmp')
import pipes_round2_eval_20261022 as e

def main():
    assert all(any(q.get('type')=='compact_summary' and k in q.get('comparisons',{}) for q in e.rows()) for k in ['recycled_deleted_band','replay_section','replay_compact_full','replay_compact_capped'])
    generator=e.Path('/tmp/pipes_openlike_round2_20261022.py')
    destination=e.Path('/tmp/pipes_openlike_round2_inputs_20261022')
    if not destination.exists():
        module=e._load_module(generator)
        manifest=module.generate(destination)
    else:manifest=destination/'manifest.jsonl'
    print('GENERATOR_INPUTS_READY',str(manifest),flush=True)
    if not any(m.get('provenance')=='round2_openlike96' for m in e.read_jsonl(e.MANIFEST)):
        e.register_fresh(manifest,generator)
    prefix_generator=e.Path('/tmp/pipes_prefix_round2_20261022.py')
    assert e.sha(prefix_generator.read_bytes())=='208b838ca41b26eab0d1e3bfeea0187d94a61d956d53a39a1681189d26bb7e9e'
    prefix_destination=e.Path('/tmp/pipes_prefix_round2_inputs_20261022')
    if not prefix_destination.exists():
        prefix_manifest=e._load_module(prefix_generator).generate(prefix_destination)
    else:prefix_manifest=prefix_destination/'manifest.jsonl'
    if not any(m.get('provenance')=='round2_prefix24' for m in e.read_jsonl(e.MANIFEST)):
        e.register_fresh(prefix_manifest,prefix_generator,expected_splits={'development':8,'sealed_final':16},provenance='round2_prefix24',id_prefix='round2-prefix-')
    print('WITNESSES_VALIDATED',120,flush=True)
    assert len(e.inputs('development'))==40

    kinds=['baseline','recycled_deleted_band','replay_section','replay_compact_full','replay_compact_capped']
    e.batch_pairs(kinds,'development')
    s=e.compact_summary(kinds[1:],'development')
    print('DEVELOPMENT_RESULT',json.dumps(s,ensure_ascii=False),flush=True)
    print('STOP_BEFORE_ALL2861_AND_FINAL',flush=True)

if __name__=='__main__':main()
