"""Falsify the archive verifier using independently constructed raw/normalized identities."""
import argparse,base64,hashlib,json,unittest
from pathlib import Path
import check_sbom_archives
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    class Cases(unittest.TestCase):
        def fixture(self,name):
            root=a.out/name;package=root/'package';cache=root/'nuget';package.mkdir(parents=True);directory=cache/'fixture'/'1.0.0';directory.mkdir(parents=True);raw=b'public synthetic archive including signature bytes';normalized=base64.b64encode(hashlib.sha512(b'normalized content excluding signature').digest()).decode();digest=hashlib.sha512(raw).hexdigest();(directory/'fixture.1.0.0.nupkg').write_bytes(raw);(directory/'.nupkg.metadata').write_text(json.dumps({'contentHash':normalized}));dep={'id':'Fixture','version':'1.0.0','nugetContentHash':normalized,'rawSignedNupkgSha512':digest};component={'name':'Fixture','versionInfo':'1.0.0','SPDXID':'SPDXRef-Component','downloadLocation':'https://api.nuget.org/v3-flatcontainer/fixture/1.0.0/fixture.1.0.0.nupkg','checksums':[{'algorithm':'SHA512','checksumValue':digest}]};(package/'DEPENDENCIES.json').write_text(json.dumps({'packages':[dep]}));(package/'SBOM.spdx.json').write_text(json.dumps({'packages':[component]}));return package,cache,dep,component
        def test_distinct_normalized_identity_and_actual_raw_checksum_pass(self):
            package,cache,_,_=self.fixture('actual');result=check_sbom_archives.verify(package,cache);self.assertFalse(result['verified'][0]['normalizedIdentityEqualsRawDigest'])
        def test_old_normalized_checksum_mislabel_is_rejected(self):
            package,cache,dep,component=self.fixture('normalized');component['checksums'][0]['checksumValue']=base64.b64decode(dep['nugetContentHash']).hex();(package/'SBOM.spdx.json').write_text(json.dumps({'packages':[component]}))
            with self.assertRaises(ValueError):check_sbom_archives.verify(package,cache)
        def test_tampered_raw_archive_is_rejected(self):
            package,cache,_,_=self.fixture('tampered');(cache/'fixture/1.0.0/fixture.1.0.0.nupkg').write_bytes(b'changed')
            with self.assertRaises(ValueError):check_sbom_archives.verify(package,cache)
        def test_matching_dependency_and_sbom_lies_still_fail_actual_bytes(self):
            package,cache,dep,component=self.fixture('paired');dep['rawSignedNupkgSha512']='0'*128;component['checksums'][0]['checksumValue']='0'*128;(package/'DEPENDENCIES.json').write_text(json.dumps({'packages':[dep]}));(package/'SBOM.spdx.json').write_text(json.dumps({'packages':[component]}))
            with self.assertRaises(ValueError):check_sbom_archives.verify(package,cache)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases));(a.out/'receipt.json').write_text(json.dumps({'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors)})+'\n');raise SystemExit(0 if result.wasSuccessful() else 1)
if __name__=='__main__':main()
