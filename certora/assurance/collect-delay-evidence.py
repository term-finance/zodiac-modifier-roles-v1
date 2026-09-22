from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import gzip
import hashlib
import json
import re
import shutil
import sys
import zipfile

import requests

TEMP = Path(sys.argv[1]).resolve()
REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / 'packages/evm/certora/assurance/evidence/delay-protection-2026-09-22'
JOBS = {'cleared-selector-submission': 'initial-sanity-failure', 'intermediate-submission': 'packed-key-diagnostic',
        'overapproximation-submission': 'all-operations-overapproximation', 'submission': 'precise-policy',
        'boundary-submission': 'independent-boundary'}


def save(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def fetch(pair):
    source, label = pair
    log = (TEMP / (source + '.log')).read_text()
    url = re.findall(r'https://prover.certora.com/output/[^\s\x1b]+', log)[-1]
    folder = ROOT / label
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'submission.log').write_text(re.sub(r'\x1b\[[0-9;]*m', '', log))
    job = url.split('/')[5].split('?')[0]
    archive = TEMP / '.certora_internal' / (job + '.zip')
    if archive.exists():
        shutil.copy2(archive, folder / 'submitted-inputs.zip')
    matches = {}
    if archive.exists():
        with zipfile.ZipFile(archive) as bundle:
            for name in ['contracts/Roles.sol', 'contracts/Permissions.sol', 'certora/harness/RolesHarness.sol',
                         'certora/specs/Roles/delayProtection.spec', 'certora/confs/Roles-delayProtection.conf']:
                member = '.certora_sources/' + name
                if member in bundle.namelist():
                    content = bundle.read(member)
                    matches[name] = {'submittedSha256': hashlib.sha256(content).hexdigest(),
                                     'matchesCurrent': content == (REPO / 'packages/evm' / name).read_bytes()}
    responses = {}
    for endpoint in ['jobData', 'progress', 'jsonOutput']:
        response = requests.get(url.replace('/output/', '/' + endpoint + '/'), timeout=50)
        response.raise_for_status()
        if response.text.strip():
            responses[endpoint] = response.json()
            save(folder / (endpoint + '.json'), responses[endpoint])
    progress = json.loads(responses.get('progress', {}).get('verificationProgress', '{}'))
    nodes, outputs = [], set()

    def walk(node):
        nodes.append(node)
        outputs.update(node.get('output') or [])
        for child in node.get('children', []):
            walk(child)

    for node in progress.get('rules', []):
        walk(node)
    output_hashes = {}
    for name in sorted(outputs):
        assert re.fullmatch(r'rule_output_\d+\.json', name)
        response = requests.get(url.replace('/output/', '/result/') + '&output=' + name, timeout=50)
        response.raise_for_status()
        json.loads(response.content)
        (folder / (name + '.gz')).write_bytes(gzip.compress(response.content, mtime=0))
        output_hashes[name] = hashlib.sha256(response.content).hexdigest()
    terminal = responses.get('progress', {}).get('jobEnded') is True
    expected_methods = {'clearanceOf(uint16,address)', 'delayVetoSelector()', 'functionScopeConfigForData(uint16,address,bytes)',
                        'multisend()', 'owner()', 'selectorForData(bytes)'}
    roots = {r['name']: r for r in progress.get('rules', [])}
    expected_roots = {'envfreeFuncsStaticCheck', 'revokedSelectorCannotBeForwarded'}
    sanity = [n for n in nodes if n.get('nodeType') == 'SANITY']
    functional = (label == 'precise-policy' and terminal and set(roots) == expected_roots
                  and {n['name'] for n in roots['envfreeFuncsStaticCheck'].get('children', [])} == expected_methods
                  and len(sanity) == 8 and nodes and all(n.get('status') == 'VERIFIED' for n in nodes)
                  and len(matches) == 5 and all(v['matchesCurrent'] for v in matches.values())
                  and responses.get('jsonOutput', {}).get('rules', {}).get('revokedSelectorCannotBeForwarded') == 'SUCCESS')
    assessment = {'reportUrl': url, 'jobStatus': responses.get('jobData', {}).get('jobStatus'), 'terminal': terminal,
                  'functionalPolicyTheoremAccepted': bool(functional), 'semanticClosureCertified': False,
                  'scope': 'Single permission-configuration transition with explicit multisend and veto exclusions; no deployment or arbitrary-history closure.',
                  'rootStatuses': {k: v.get('status') for k, v in roots.items()}, 'sanityInstanceCount': len(sanity),
                  'inputComparison': matches, 'availableOutputCount': len(outputs), 'retainedOutputCount': len(output_hashes),
                  'uncompressedOutputSha256': output_hashes}
    save(folder / 'assessment.json', assessment)
    save(folder / 'manifest.json', {'filesSha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                                 for p in sorted(folder.iterdir()) if p.is_file() and p.name != 'manifest.json'},
                                  'semanticClosureCertified': False})
    print(label, assessment['jobStatus'], assessment['rootStatuses'], 'policy accepted:', functional, flush=True)
    return {label: assessment}


if __name__ == '__main__':
    ROOT.mkdir(parents=True, exist_ok=True)
    result = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for item in pool.map(fetch, JOBS.items()):
            result.update(item)
    save(ROOT / 'index.json', result)
