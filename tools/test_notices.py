"""Regression for expression-only NuGet packages and missing/tampered license text."""
import argparse,json,shutil,unittest,xml.etree.ElementTree as ET
from pathlib import Path
import notices
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    records=json.loads((ROOT/'vendor/notices/NOTICE-SOURCES.json').read_text())['components']
    class Cases(unittest.TestCase):
        def metadata(self,record):
            root=ET.Element('metadata');ET.SubElement(root,'license',{'type':'expression'}).text=record['license'];ET.SubElement(root,'copyright').text=record['copyright'];return root
        def record(self,name):return next(r for r in records if r['id']==name)
        def fixture(self,name):
            directory=a.out/name;directory.mkdir();(directory/'vendor').mkdir();shutil.copytree(ROOT/'vendor/notices',directory/'vendor/notices');package=directory/'package';package.mkdir();return directory,package
        def test_expression_only_npgsql_gets_exact_vendored_text(self):
            repo,package=self.fixture('npgsql');record=self.record('Npgsql');value=notices.resolve(repo,package,'Npgsql/10.0.3',{'sha512':record['nugetContentHash']},self.metadata(record));self.assertIn(b'Copyright (c) 2002-2025, Npgsql',value['primary'].read_bytes())
        def test_missing_full_license_fails_instead_of_shipping_expression_only(self):
            repo,package=self.fixture('missing');record=self.record('Npgsql');(repo/'vendor/notices'/record['licenseSource']['file']).unlink()
            with self.assertRaises(ValueError):notices.resolve(repo,package,'Npgsql/10.0.3',{'sha512':record['nugetContentHash']},self.metadata(record))
        def test_changed_microsoft_license_fails_even_with_mit_expression(self):
            repo,package=self.fixture('changed');record=self.record('Microsoft.Extensions.Logging.Abstractions');(repo/'vendor/notices'/record['licenseSource']['file']).write_text('MIT')
            with self.assertRaises(ValueError):notices.resolve(repo,package,record['id']+'/'+record['version'],{'sha512':record['nugetContentHash']},self.metadata(record))
        def test_missing_copyright_and_unknown_graph_fail_closed(self):
            repo,package=self.fixture('metadata');record=self.record('Npgsql');meta=self.metadata(record);meta.find('copyright').text=''
            with self.assertRaises(ValueError):notices.resolve(repo,package,'Npgsql/10.0.3',{'sha512':record['nugetContentHash']},meta)
            with self.assertRaises(ValueError):notices.resolve(repo,package,'Npgsql/99.0.0',{'sha512':record['nugetContentHash']},self.metadata(record))
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Cases);result=unittest.TextTestRunner(verbosity=2).run(suite)
    receipt={'status':'PASS' if result.wasSuccessful() else 'FAIL','run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'scope':'Pinned notice resolution, missing/corrupted full license and copyright/graph denial'}
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');raise SystemExit(0 if result.wasSuccessful() else 1)

if __name__=='__main__':main()
