from work import *
from concurrent.futures import ThreadPoolExecutor

commands = [
    ('doctor-project',cli('doctor-project','--project-root',ROOT)),
    ('context-after-docs',cli('project-context-check','--project-root',ROOT,'--workplace',WP,'--json','--check-update-candidates','never')),
    ('documentation-diff-check',['git','diff','--check','--',*[str(ROOT/'.pf/artifacts'/x) for x in __import__('inventory').TARGETS]])
]

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda pair:command(*pair),commands))
    context=json.loads(results[1])
    assert context['fresh'] and context['execution_readiness']['status']=='ready'
    log('Documentation quality commands','commands/doctor-project.json, context-after-docs.json, documentation-diff-check.json','Commands passed; current context fresh and ready','Review all artifact content and final delivery references')
