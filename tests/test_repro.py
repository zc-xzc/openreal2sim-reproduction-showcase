"""Synthetic offline harness tests. No upstream imports, networking, or GPU claims."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import pickle
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import sys

spec = importlib.util.spec_from_file_location("repro", Path(__file__).resolve().parents[1]/"scripts/repro.py")
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
try:
    import numpy as np
except ImportError:
    np = None

def glb():
    payload = json.dumps({"asset":{"version":"2.0"}}).encode()
    payload += b" " * (-len(payload) % 4)
    return struct.pack("<4sII",b"glTF",2,20+len(payload))+struct.pack("<I4s",len(payload),b"JSON")+payload

class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def write(self,name,data=b"x"):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(data if isinstance(data,bytes) else data.encode());return p
    def fail(self,fn,*args,**kwargs):
        with self.assertRaises(r.CheckError):fn(*args,**kwargs)
    def fixture(self):
        base="outputs/demo/simulation/"
        for name in ("bg.glb","scene.glb","obj.glb"):self.write(base+name,glb())
        for name in ("bg.jpg","fd.npy","simple.npy","hybrid.npy"):self.write(base+name)
        data={"background_image":"bg.jpg","background":{"registered":"bg.glb"},"scene_mesh":{"optimized":"scene.glb"},"objects":{"1":{"optimized":"obj.glb","fdpose_trajs":"fd.npy","simple_trajs":"simple.npy","hybrid_trajs":"hybrid.npy"}}}
        self.write(base+"scene.json",json.dumps(data));return data
    def masks(self,objects=None,shape=(1,4,5,3)):
        def obj(name):return {"name":name,"bbox":[0,0,4,3],"mask":np.ones((4,5),dtype=bool)}
        scene={"images":np.zeros(shape,dtype=np.uint8),"mask":{0:objects or {1:obj("ground"),2:obj("cup")}}}
        self.write("outputs/demo/scene/scene.pkl",pickle.dumps(scene));return scene
    def test_valid_key(self): self.assertEqual(r.key_name("demo_01-x"),"demo_01-x")
    def test_invalid_key(self):
        for value in ("../x","","-bad","a/b","x"*81,"a b"):
            self.fail(r.key_name,value)
    def test_path_escape(self):self.fail(r.confined,self.root,"../outside")
    def test_absolute_escape(self):self.fail(r.confined,self.root,"/etc/passwd")
    def test_symlink_escape(self):
        (self.root/"link").symlink_to(self.root.parent);self.fail(r.confined,self.root,"link/x")
    def test_valid_confined(self):self.assertEqual(r.confined(self.root,"a"),self.root/"a")
    def test_empty_inventory(self):self.fail(r.inventory,self.root,["missing"])
    def test_inventory_hash(self):
        p=self.write("weights/a",b"abc");out=r.inventory(self.root,["weights"])
        self.assertEqual(out["files"][0]["sha256"],r.sha256(p))
    def test_asset_valid(self):
        self.write("w");m=self.write("lock.json",json.dumps(r.inventory(self.root,["w"])))
        self.assertEqual(r.verify_asset_lock(self.root,m)["files_verified"],1)
    def test_asset_changed(self):
        self.write("w");m=self.write("lock.json",json.dumps(r.inventory(self.root,["w"])));self.write("w",b"changed")
        self.fail(r.verify_asset_lock,self.root,m)
    def test_asset_empty(self):self.fail(r.verify_asset_lock,self.root,self.write("m",'{"files":[]}'))
    def test_asset_bad_hash(self):
        self.fail(r.verify_asset_lock,self.root,self.write("m",'{"files":[{"path":"w","sha256":"fake"}]}'))
    def test_asset_escape(self):
        m=self.write("m",json.dumps({"files":[{"path":"../bad","sha256":"a"*64}]}))
        self.fail(r.verify_asset_lock,self.root,m)
    def test_glb_valid(self):r.check_glb(self.write("g",glb()))
    def test_glb_empty(self):self.fail(r.check_glb,self.write("g",b""))
    def test_glb_header_only(self):self.fail(r.check_glb,self.write("g",struct.pack("<4sII",b"glTF",2,12)))
    def test_glb_bad_length(self):self.fail(r.check_glb,self.write("g",glb()+b"x"))
    def test_glb_bad_json(self):
        self.fail(r.check_glb,self.write("g",struct.pack("<4sII",b"glTF",2,24)+struct.pack("<I4s",4,b"JSON")+b"xxxx"))
    def test_artifact_full(self):
        self.fixture();self.assertTrue(r.check_artifacts(self.root,"demo","reconstruct")["pass"])
    def test_missing_trajectory(self):
        self.fixture();(self.root/"outputs/demo/simulation/fd.npy").unlink()
        self.fail(r.check_artifacts,self.root,"demo","reconstruct")
    def test_reference_escape(self):
        d=self.fixture();d["background_image"]="../private.jpg"
        self.write("outputs/demo/private.jpg");self.write("outputs/demo/simulation/scene.json",json.dumps(d))
        self.fail(r.check_artifacts,self.root,"demo","reconstruct")
    def test_preprocess_images_not_resized(self):
        self.write("outputs/demo/scene/scene.pkl");self.write("outputs/demo/images/frame_00000.jpg")
        self.assertEqual(r.check_artifacts(self.root,"demo","preprocess")["frame_count"],1)
    def test_preprocess_missing_images(self):
        self.write("outputs/demo/scene/scene.pkl");self.write("outputs/demo/resized_images/000000.jpg")
        self.fail(r.check_artifacts,self.root,"demo","preprocess")
    def test_pickle_gate(self):self.fail(r.check_masks,self.root,"demo")
    @unittest.skipIf(np is None,"NumPy not installed")
    def test_mask_valid(self):
        self.masks();self.assertTrue(r.check_masks(self.root,"demo",True)["pass"])
    @unittest.skipIf(np is None,"NumPy not installed")
    def test_mask_wrong_shape(self):
        d=self.masks();d["mask"][0][2]["mask"]=np.ones((2,2),dtype=bool)
        self.write("outputs/demo/scene/scene.pkl",pickle.dumps(d));self.fail(r.check_masks,self.root,"demo",True)
    @unittest.skipIf(np is None,"NumPy not installed")
    def test_mask_missing(self):
        d=self.masks();del d["mask"]
        self.write("outputs/demo/scene/scene.pkl",pickle.dumps(d));self.fail(r.check_masks,self.root,"demo",True)
    @unittest.skipIf(np is None,"NumPy not installed")
    def test_mask_hand_not_object(self):
        d=self.masks();d["mask"][0][2]["name"]="hand"
        self.write("outputs/demo/scene/scene.pkl",pickle.dumps(d));self.fail(r.check_masks,self.root,"demo",True)
    @unittest.skipIf(np is None,"NumPy not installed")
    def test_mask_no_frame_zero(self):
        d=self.masks();d["mask"][1]=d["mask"].pop(0)
        self.write("outputs/demo/scene/scene.pkl",pickle.dumps(d));self.fail(r.check_masks,self.root,"demo",True)
    @unittest.skipIf(np is None,"NumPy not installed")
    def test_mask_filename_escape(self):
        d=self.masks();d["mask"][0][2]["name"]="../cup"
        self.write("outputs/demo/scene/scene.pkl",pickle.dumps(d));self.fail(r.check_masks,self.root,"demo",True)
    def test_annotator_key_and_private(self):
        cmd=r.command("annotate","demo");self.assertIn("--key",cmd);self.assertIn("127.0.0.1",cmd);self.assertNotIn("--share",cmd)
    def test_preprocess_cli(self):
        self.assertEqual(r.command("preprocess","demo")[-2:],["--key_name","demo"])
    def test_dry_run_no_side_effect(self):
        before=list(self.root.rglob("*"))
        with patch.object(r.subprocess,"run",side_effect=AssertionError("must not execute")),contextlib.redirect_stdout(io.StringIO()):
            rc=r.main(["run","--root",str(self.root),"--key","demo","--stage","preprocess","--report",str(self.root/"never.json")])
        self.assertEqual(rc,0);self.assertEqual(before,list(self.root.rglob("*")))
    def test_no_trust_no_execute(self):
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()),patch.object(r.subprocess,"run",side_effect=AssertionError):
            self.assertEqual(r.main(["run","--execute","--root",str(self.root),"--key","demo","--stage","motion"]),1)
    def test_emit_wont_overwrite(self):self.fail(r.emit,{},self.write("report"))
    def setup_run(self,stage="motion"):
        self.write("config/config.yaml",'keys: [demo]\nlocal: {}\n')
        self.write("assets.json",'{"files": []}')
        return SimpleNamespace(root=self.root,key="demo",stage=stage,execute=True,trust_local_code=True,report=self.root/"report.json",assets_lock=self.root/"assets.json",trust_local_pickle=True,resume=False)
    def execute_mock(self,args,returncode=0,artifact_side=None):
        fake_yaml=SimpleNamespace(safe_load=lambda x:{"keys":["demo"],"local":{}})
        with patch.dict(sys.modules,{"yaml":fake_yaml}),patch.object(r,"source_check"),patch.object(r,"verify_asset_lock"),patch.object(r,"capture",return_value={}),patch.object(r,"check_artifacts",side_effect=artifact_side),patch.object(r.subprocess,"run",return_value=SimpleNamespace(returncode=returncode)) as proc,contextlib.redirect_stdout(io.StringIO()):
            result=r.run(args)
            return result,proc
    def test_run_failure_exit(self):
        args=self.setup_run();rc,proc=self.execute_mock(args,7)
        self.assertEqual(rc,1);self.assertEqual(json.loads(args.report.read_text())["status"],"process_failed")
    def test_run_offline_flags(self):
        rc,proc=self.execute_mock(self.setup_run());env=proc.call_args.kwargs["env"]
        self.assertEqual(env["HF_HUB_OFFLINE"],"1");self.assertEqual(env["GRADIO_ANALYTICS_ENABLED"],"False")
    def test_run_validation_failure_exit(self):
        args=self.setup_run("preprocess");self.write("data/demo.jpg")
        rc,_=self.execute_mock(args,artifact_side=ValueError("bad json"))
        self.assertEqual(rc,1);self.assertEqual(json.loads(args.report.read_text())["status"],"failed_or_interrupted")
    def test_preprocess_reject_existing(self):
        args=self.setup_run("preprocess");self.write("outputs/demo/stale")
        with patch.object(r,"source_check"):self.fail(r.run,args)
    def test_preprocess_reject_ambiguous_input(self):
        args=self.setup_run("preprocess");self.write("data/demo.jpg");self.write("data/demo.mp4")
        with patch.object(r,"source_check"):self.fail(r.run,args)
    def test_preprocess_reject_only_depth(self):
        args=self.setup_run("preprocess");self.write("data/demo_depth.png")
        with patch.object(r,"source_check"):self.fail(r.run,args)
    def test_motion_requires_pickle_trust(self):
        args=self.setup_run();args.trust_local_pickle=False
        with patch.object(r,"source_check",side_effect=AssertionError):self.fail(r.run,args)
    def test_run_records_config_model_patch_hashes(self):
        args=self.setup_run();rc,_=self.execute_mock(args)
        data=json.loads(args.report.read_text())
        self.assertEqual(data["config_sha256"],r.sha256(self.root/"config/config.yaml"))
        self.assertEqual(data["asset_manifest_sha256"],r.sha256(args.assets_lock))
        self.assertEqual(len(data["patch_sha256"]),64)
    def test_source_reject_head(self):
        with patch.object(r,"git",return_value="wrong"):self.fail(r.source_check,self.root)
    def test_source_reject_unrelated_drift(self):
        self.write("locks/source-lock.json",json.dumps({"submodules":[],"patched_files":{"allowed.py":"a"*64}}))
        with patch.object(r,"HERE",self.root),patch.object(r,"git",side_effect=[r.PIN,"evil.py"]):
            self.fail(r.source_check,self.root,require_submodules=False)
    def test_source_reject_patch_hash(self):
        self.write("allowed.py");self.write("locks/source-lock.json",json.dumps({"submodules":[],"patched_files":{"allowed.py":"a"*64}}))
        with patch.object(r,"HERE",self.root),patch.object(r,"git",side_effect=[r.PIN,"allowed.py"]):
            self.fail(r.source_check,self.root,require_submodules=False)

if __name__=="__main__":unittest.main()
