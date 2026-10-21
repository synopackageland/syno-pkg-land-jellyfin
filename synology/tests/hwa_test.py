import os,pathlib,subprocess,tempfile,unittest,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'container/hwa.sh'

class HWATests(unittest.TestCase):
 def run_hwa(self,state,**env):
  return subprocess.run(['sh','-c','. "$1"; hwa_setup "$2"','hwa',str(SCRIPT),str(state)],env={**os.environ,**env},text=True,capture_output=True)
 def test_probe_tolerates_cold_library_loading_and_propagates_failure(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);ffmpeg=p/'ffmpeg';adapter=p/'hwa.sh'
   ffmpeg.write_text('#!/bin/sh\nsleep 16\nexit 0\n');ffmpeg.chmod(0o700)
   adapter.write_text(SCRIPT.read_text().replace('/usr/lib/jellyfin-ffmpeg/ffmpeg',str(ffmpeg)))
   command=['sh','-c','. "$1"; hwa_probe /dev/dri/renderD128','hwa',str(adapter)]
   r=subprocess.run(command,text=True,capture_output=True,timeout=25)
   self.assertEqual(r.returncode,0,r.stderr)
   ffmpeg.write_text('#!/bin/sh\nexit 42\n')
   r=subprocess.run(command,text=True,capture_output=True,timeout=5)
   self.assertEqual(r.returncode,42)
 def test_native_vaapi_configuration_and_existing_settings(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)
   args=['sh','-c','. "$1"; hwa_write "$2" vaapi /dev/dri/renderD128','hwa',str(SCRIPT),str(p)]
   r=subprocess.run(args,text=True,capture_output=True);self.assertEqual(r.returncode,0,r.stderr)
   f=p/'config/config/encoding.xml';xml=ET.parse(f)
   self.assertEqual(xml.findtext('HardwareAccelerationType'),'vaapi');self.assertEqual(xml.findtext('VaapiDevice'),'/dev/dri/renderD128')
   self.assertEqual(xml.findtext('EnableHardwareEncoding'),'true')
   f.write_text('<EncodingOptions><H264Crf>19</H264Crf><HardwareAccelerationType>none</HardwareAccelerationType></EncodingOptions>')
   r=subprocess.run(args,text=True,capture_output=True);self.assertEqual(r.returncode,0,r.stderr)
   self.assertEqual(ET.parse(f).findtext('H264Crf'),'19')
 def test_absent_device_preserves_software_and_other_settings(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);config=p/'config/config';config.mkdir(parents=True)
   f=config/'encoding.xml';f.write_text('<EncodingOptions><HardwareAccelerationType>vaapi</HardwareAccelerationType><H264Crf>19</H264Crf></EncodingOptions>')
   r=self.run_hwa(p,SYNOPKGLAND_GPU_STATUS='software')
   self.assertEqual(r.returncode,0,r.stderr)
   xml=ET.parse(f);self.assertEqual(xml.findtext('HardwareAccelerationType'),'none');self.assertEqual(xml.findtext('H264Crf'),'19')
 def test_missing_device_never_enables_hardware(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)
   r=self.run_hwa(p,SYNOPKGLAND_GPU_STATUS='available',SYNOPKGLAND_GPU_DEVICE='/dev/dri/renderD128')
   self.assertEqual(r.returncode,0,r.stderr)
   self.assertFalse((p/'config/config/encoding.xml').exists())
 def test_arbitrary_path_rejected_without_using_it(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)
   r=self.run_hwa(p,SYNOPKGLAND_GPU_STATUS='available',SYNOPKGLAND_GPU_DEVICE='/dev/null')
   self.assertEqual(r.returncode,0,r.stderr)
   self.assertFalse((p/'config/config/encoding.xml').exists())

if __name__=='__main__': unittest.main()
