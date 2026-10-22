"""Assemble the pinned beta archive in GitHub; never publish or replace assets."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

MANIFEST = {'repository': 'supaplayabusiness/VoiceDictation-releases', 'source_release_id': 421306518, 'source_tag': 'platform-voice-transfer-1.14.3-build11403', 'target_release_id': 421302717, 'target_tag': 'platform-macos-v0.8.07', 'final_name': 'platform-voice-1.14.3-build11403.zip', 'final_bytes': 110272059, 'final_sha256': '52d98403bc7e9d311cb713853836f67502bb363e15ad19fe2a1f9227d339c788', 'parts': [{'index': 0, 'name': 'voice-1.14.3-build11403.part000', 'bytes': 10485760, 'sha256': '15c4884aaa4b9287805f995cd8b484e536a1d500e6cdc78e83ee2deaaf9f1ce3'}, {'index': 1, 'name': 'voice-1.14.3-build11403.part001', 'bytes': 10485760, 'sha256': '9a9df46a205b681103f1725a7f40a24ff2009c3e1a3da6f215cd6b6fbeb3f0c7'}, {'index': 2, 'name': 'voice-1.14.3-build11403.part002', 'bytes': 10485760, 'sha256': '20dcede86247b508c1fc9fbba5a1e3ddfade82713a49193c9de38d59afbb586e'}, {'index': 3, 'name': 'voice-1.14.3-build11403.part003', 'bytes': 10485760, 'sha256': 'a10d67f7a9435bd05dc7c6b193ca447c11bc6a4cc379d5097ca2c6db448c9de4'}, {'index': 4, 'name': 'voice-1.14.3-build11403.part004', 'bytes': 10485760, 'sha256': 'a87c2b81c8726c3d3ab758377d9752daca8c62072d2ee72d93d6b2710cf5167f'}, {'index': 5, 'name': 'voice-1.14.3-build11403.part005', 'bytes': 10485760, 'sha256': '7127532e6ad86f2d53d290b78ce063c5a7803ba456ac86e13fc6f52cccf82f47'}, {'index': 6, 'name': 'voice-1.14.3-build11403.part006', 'bytes': 10485760, 'sha256': '883677a271c17d726153f54488376d0b6d5bdfc533eff5f96d4bf3152bb99c21'}, {'index': 7, 'name': 'voice-1.14.3-build11403.part007', 'bytes': 10485760, 'sha256': '80623ffb1e84cd64cfca7c698acab60d083189542f56e30428e4b4e0d9c87b0a'}, {'index': 8, 'name': 'voice-1.14.3-build11403.part008', 'bytes': 10485760, 'sha256': '26490a5bb0c74be32e15d94883bfa48b03d04e57e0353ed7de381ee7361c2094'}, {'index': 9, 'name': 'voice-1.14.3-build11403.part009', 'bytes': 10485760, 'sha256': '3a1802c328d79733dba4f2fc164c3328a669bd572e748cb13120e65698ea00d5'}, {'index': 10, 'name': 'voice-1.14.3-build11403.part010', 'bytes': 5414459, 'sha256': '6b4304da5af1a358c1e4e94b9827b7081565662621088ea99958f285c7e9d2f0'}], 'target_existing_assets': [{'id': 667398898, 'name': 'platform-file-tools-0.8.07-build14.zip', 'size': 18136168, 'state': 'uploaded', 'digest': 'sha256:6c2380d2788eb65c59f7875e7d76d750f9bccfd637cdb494e88475debdcc32d3'}, {'id': 667401419, 'name': 'platform-reader-0.8.07-build14.zip', 'size': 1448420, 'state': 'uploaded', 'digest': 'sha256:4f636df6903707f7da7d3573bac7929f42fa96829b651fc9122cef9ce9d290c2'}]}

def gh(*args):
    p = subprocess.run(['gh', *args], capture_output=True, text=True, timeout=180)
    if p.returncode: raise RuntimeError('GitHub transfer operation failed')
    return p.stdout

def api(suffix):
    return json.loads(gh('api', 'repos/'+MANIFEST['repository']+'/'+suffix))

def metadata(asset):
    return {k:asset[k] for k in ['id','name','size','state','digest']}

def check_asset(asset, name, size, digest):
    assert asset['name']==name and asset['state']=='uploaded'
    assert asset['size']==size and asset['digest']=='sha256:'+digest

def check_target(target):
    assert target['id']==MANIFEST['target_release_id'] and target['tag_name']==MANIFEST['target_tag']
    assert target['draft'] and target['prerelease']
    other=[metadata(a) for a in target['assets'] if a['name']!=MANIFEST['final_name']]
    assert sorted(other,key=lambda a:a['id'])==sorted(MANIFEST['target_existing_assets'],key=lambda a:a['id'])
    own=[a for a in target['assets'] if a['name']==MANIFEST['final_name']]
    assert len(own)<=1
    if own: check_asset(own[0],MANIFEST['final_name'],MANIFEST['final_bytes'],MANIFEST['final_sha256'])
    return own

def verify(path, size, digest):
    assert path.is_file() and not path.is_symlink() and path.stat().st_size==size
    h=hashlib.sha256()
    with path.open('rb') as stream:
        while chunk:=stream.read(1024*1024):h.update(chunk)
    assert h.hexdigest()==digest

def main():
    assert os.environ.get('GITHUB_REPOSITORY')==MANIFEST['repository']
    source=api('releases/'+str(MANIFEST['source_release_id']))
    assert source['draft'] and source['prerelease'] and source['tag_name']==MANIFEST['source_tag']
    parts=MANIFEST['parts'];assets={a['name']:a for a in source['assets']}
    assert len(parts)==11 and set(assets)=={p['name'] for p in parts}
    assert sum(p['bytes'] for p in parts)==MANIFEST['final_bytes']
    latest=api('releases/latest')['id']
    target=api('releases/'+str(MANIFEST['target_release_id']));check_target(target)
    with tempfile.TemporaryDirectory(prefix='voice-reviewed-') as directory:
        root=Path(directory);final=root/MANIFEST['final_name']
        with final.open('xb') as assembled:
            for index,part in enumerate(parts):
                assert part['index']==index and part['name']==f'voice-1.14.3-build11403.part{index:03d}'
                check_asset(assets[part['name']],part['name'],part['bytes'],part['sha256'])
                path=root/part['name']
                gh('release','download',MANIFEST['source_tag'],'--repo',MANIFEST['repository'],'--pattern',part['name'],'--output',str(path))
                verify(path,part['bytes'],part['sha256'])
                with path.open('rb') as stream:
                    while chunk:=stream.read(1024*1024):assembled.write(chunk)
                path.unlink()
        verify(final,MANIFEST['final_bytes'],MANIFEST['final_sha256'])
        target=api('releases/'+str(MANIFEST['target_release_id']))
        if not check_target(target):
            gh('release','upload',MANIFEST['target_tag'],str(final),'--repo',MANIFEST['repository'])
        assert len(check_target(api('releases/'+str(MANIFEST['target_release_id']))))==1
        downloaded=root/'uploaded-copy.zip'
        gh('release','download',MANIFEST['target_tag'],'--repo',MANIFEST['repository'],'--pattern',MANIFEST['final_name'],'--output',str(downloaded))
        verify(downloaded,MANIFEST['final_bytes'],MANIFEST['final_sha256'])
    assert api('releases/latest')['id']==latest
    assert [metadata(a) for a in api('releases/'+str(MANIFEST['source_release_id']))['assets']]==[metadata(a) for a in source['assets']]
    print('PASS pinned archive assembled and re-downloaded; target remains draft; original assets and Latest unchanged')

if __name__=='__main__':main()
