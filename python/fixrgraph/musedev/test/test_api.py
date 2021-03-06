""" Test the creation of the index

"""

import sys
import logging
import os
import json
import copy
import subprocess
import tempfile
import shutil

from flask import Flask, Response
from multiprocessing import Process
from cStringIO import StringIO

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from fixrgraph.wireprotocol.search_service_wire_protocol import decompress
from fixrgraph.musedev.biggroumscript import main
from fixrgraph.musedev.api import (
    biggroum_api_map,
    GRAPH_EXTRACTOR_PATH, FIXR_SEARCH_ENDPOINT
)
from fixrgraph.musedev.residue import Residue
import fixrgraph.musedev.test

def compare_json_obj(obj1, obj2):
    if (json.dumps(obj1, sort_keys=True) == json.dumps(obj2, sort_keys=True)):
        return True
    else:
        print(json.dumps(obj1, indent=2, sort_keys=True))
        print(json.dumps(obj2, indent=2, sort_keys=True))
        return False

def get_extractor_path():
    # TODO: refactor with TestPipeline (move all tests together)
    repo_path = os.path.abspath(os.path.dirname(fixrgraph.musedev.test.__file__))
    repo_path = os.path.join(repo_path, os.pardir)
    repo_path = os.path.join(repo_path, os.pardir)
    repo_path = os.path.join(repo_path, os.pardir)
    repo_path = os.path.join(repo_path, os.pardir)
    repo_path = os.path.abspath(repo_path)
    extractor_path = os.path.join(repo_path,
                                  "FixrGraphExtractor/target/scala-2.12/" \
                                  "fixrgraphextractor_2.12-0.1.0-one-jar.jar")
    return extractor_path

class TestScript(unittest.TestCase):
    FILEPATH = os.path.join(os.path.dirname(__file__), "data")
    JAVAFILE = "AwesomeApp/app/src/main/java/fixr/plv/colorado/edu/awesomeapp/MainActivity.java"
    COMMIT = "04f68b69a6f9fa254661b481a757fa1c834b52e1"

    ANOMALY1 = {
        "className": "fixr.plv.colorado.edu.awesomeapp.MainActivity",
        "methodName": "showDialog",
        "error": "missing method calls",
        "pattern": "android.app.AlertDialog$Builder.<init>($r11, $r12);\n$r13 = android.app.AlertDialog$Builder.setTitle(builder, \"\\u027e\\ufffd\\ufffd\");\n",
        "packageName": "fixr.plv.colorado.edu.awesomeapp",
        "patch": "public void showDialog(android.content.Context context) {\n    android.app.AlertDialog.Builder dialogBuilder = new android.app.AlertDialog.Builder(context);\n    java.lang.String title = \"Empty Field(s)\";\n    java.lang.String message = \"Please ensure all fields are contain data\";\n    dialogBuilder.setMessage(message);\n    dialogBuilder.setNegativeButton(\"OK\", new android.content.DialogInterface.OnClickListener() {\n        @java.lang.Override\n        public void onClick(android.content.DialogInterface dialog, int which) {\n        }\n    });\n    dialogBuilder.setPositiveButton(\"Cancel\", new android.content.DialogInterface.OnClickListener() {\n        public void onClick(android.content.DialogInterface dialog, int which) {\n            // continue with delete\n        }\n    });\n    dialogBuilder.create();\n    dialogBuilder.show();\n    // [0] The change should end here (before calling the method exit)\n}",
        "line": 47,
        "id": 1,
        "fileName": "[MainActivity.java](https://github.com/cuplv/AwesomeApp/blob/04f68b69a6f9fa254661b481a757fa1c834b52e1/app/src/main/java/fixr/plv/colorado/edu/awesomeapp/MainActivity.java)"
    }

    ANOMALY2 = {
        "className": "fixr.plv.colorado.edu.awesomeapp.MainActivity",
        "methodName": "showDialog",
        "error": "missing method calls",
        "pattern": "android.app.AlertDialog$Builder.<init>($r0, this);\n$r1 = android.app.AlertDialog$Builder.setTitle($r0, \"Exit\");\n",
        "packageName": "fixr.plv.colorado.edu.awesomeapp",
        "patch": "public void showDialog(android.content.Context context) {\n    android.app.AlertDialog.Builder dialogBuilder = new android.app.AlertDialog.Builder(context);\n    java.lang.String title = \"Empty Field(s)\";\n    java.lang.String message = \"Please ensure all fields are contain data\";\n    dialogBuilder.setMessage(message);\n    dialogBuilder.setNegativeButton(\"OK\", new android.content.DialogInterface.OnClickListener() {\n        @java.lang.Override\n        public void onClick(android.content.DialogInterface dialog, int which) {\n        }\n    });\n    dialogBuilder.setPositiveButton(\"Cancel\", new android.content.DialogInterface.OnClickListener() {\n        public void onClick(android.content.DialogInterface dialog, int which) {\n            // continue with delete\n        }\n    });\n    dialogBuilder.create();\n    dialogBuilder.show();\n    // [0] The change should end here (before calling the method exit)\n}",
        "line": 47,
        "id": 2,
        "fileName": "[MainActivity.java](https://github.com/cuplv/AwesomeApp/blob/04f68b69a6f9fa254661b481a757fa1c834b52e1/app/src/main/java/fixr/plv/colorado/edu/awesomeapp/MainActivity.java)"
    }

    class TestSearchService:
        @staticmethod
        def process():
            expected_output = [TestScript.ANOMALY1, TestScript.ANOMALY2]
            return Response(json.dumps(expected_output),
                            status=200,
                            mimetype='application/json')

        @staticmethod
        def run_service(app):
            app.run(
                host = "localhost",
                port = 8081
            )

        def __init__(self):
            self.app = Flask(__name__)
            self.app.route('/process_muse_data', methods=['POST'])(
                TestScript.TestSearchService.process)
            self.server = Process(target=TestScript.TestSearchService.run_service,
                                  args=[(self.app)])
            self.server.start()

        def stop(self):
            self.server.terminate()
            self.server.join()

    @staticmethod
    def get_args(cmd):
        return ["biggroumscript.py",
                TestScript.FILEPATH,
                TestScript.COMMIT,
                cmd,
                get_extractor_path(),
                "http://localhost:8081/process_muse_data"
        ]

    def test_applicable(self):
        myinput = StringIO()
        outstream = StringIO()
        self.assertTrue(main(TestScript.get_args("applicable"),
                             myinput,
                             outstream,
                             biggroum_api_map) == 0)
        self.assertTrue(outstream.getvalue() == "true")

    def test_version(self):
        myinput = StringIO()
        outstream = StringIO()

        self.assertTrue(main(TestScript.get_args("version"),
                             myinput,
                             outstream,
                             biggroum_api_map) == 0)
        self.assertTrue(outstream.getvalue() == "3")


    def test_run(self):
        # Mock for calling run multiple times
        runs = []
        for file_name in [TestScript.JAVAFILE, TestScript.JAVAFILE]:
            runs.append({"cwd" : "", "cmd" : "", "args" : "",
                         "classpath" : [],
                         "files": [file_name]})

        residue = {"residue" : {}}
        for run in runs:
            outstream = StringIO()

            myinput = StringIO()
            run["residue"] = residue["residue"]
            myinput.write(json.dumps(run))
            myinput.reset()

            self.assertTrue(main(TestScript.get_args("run"),
                                 myinput, outstream, biggroum_api_map) == 0)

            try:
                residue_json = outstream.getvalue()
                residue = json.loads(residue_json)
            except:
                raise Exception("Malformed JSON")

        expected_res = {
            "residue": {
                "compilation_infos" : [{"cwd" : "", "cmd" : "", "args" : "",
                                        "classpath" : [],
                                        "files": [file_name]},
                                       {"cwd" : "", "cmd" : "", "args" : "",
                                        "classpath" : [],
                                        "files": [file_name]}
                ]},
            "toolNotes": []
        }

        self.assertTrue(compare_json_obj(residue, expected_res))

    def test_finalize(self):
        myinput, outstream = StringIO(), StringIO()

        # Extract the app data
        tmpdir = tempfile.mkdtemp("tmp_test_finalize")
        try:
            app_zip = os.path.join(os.path.dirname(__file__), "data", "AwesomeApp.zip")
            decompress(app_zip, tmpdir)

            # Create a mock residue from run
            main_act_path = os.path.join(tmpdir,TestScript.JAVAFILE)
            input_res = {
                "residue": {
                    "compilation_infos" : [{"cwd" : "", "cmd" : "", "args" : "",
                                            "classpath" : [],
                                            "files": [main_act_path]}
                                           ]},
                "toolNotes": []
            }
            myinput.write(json.dumps(input_res))
            myinput.reset()

            # Start a mock service
            service = TestScript.TestSearchService()
            try:
                args = TestScript.get_args("finalize")
                args[1] = tmpdir # set the working directory

                api_res = main(args, myinput, outstream, biggroum_api_map)
                self.assertTrue(api_res == 0)

                out_json = json.loads(outstream.getvalue())

                res_path = os.path.abspath(os.path.dirname(fixrgraph.musedev.test.__file__))
                res_path = os.path.join(res_path, "data", "finalize_result.json")
                with open(res_path, 'r') as f:
                    expected_res = json.load(f)

                self.assertTrue(compare_json_obj(out_json["toolNotes"],
                                                 expected_res["toolNotes"]))

                self.assertTrue(compare_json_obj(out_json["residue"]["anomalies"],
                                                 expected_res["residue"]["anomalies"]))

            finally:
                service.stop()
        finally:
            shutil.rmtree(tmpdir)

    def test_talk(self):
        residue_empty = {
            "anomalies" : {}
        }

        inputs_errors = [
            {"residue" : {}, "messageText" : "biggroum", "user" : "", "noteID" : ""},
            {"residue" : {}, "messageText" : "biggroum wrongrequest", "user" : "", "noteID" : ""},
            {"residue" : {}, "messageText" : "biggroum inspect", "user" : ""},
            {"residue" : {}, "messageText" : "biggroum pattern", "user" : ""},
            {"residue" : residue_empty, "messageText" : "biggroum inspect", "user" : "", "noteID" : "1"},
            {"residue" : residue_empty, "messageText" : "biggroum pattern", "user" : "", "noteID" : "1"},
        ]


        for single_input in inputs_errors:
            myinput, outstream = StringIO(), StringIO()
            myinput.write(json.dumps(single_input))
            myinput.reset()
            self.assertTrue(main(TestScript.get_args("talk"),
                                 myinput, outstream, biggroum_api_map) != 0)

        residue = {
            "anomalies" : {
                "1" : TestScript.ANOMALY1,
                "2" : TestScript.ANOMALY2
            }
        }

        myinput, outstream = StringIO(), StringIO()
        myinput.write(json.dumps({"residue" : residue,
                                  "messageText" : "biggroum inspect",
                                  "user" : "", "noteID" : u'1'},))
        myinput.reset()
        self.assertTrue(main(TestScript.get_args("talk"),
                             myinput, outstream, biggroum_api_map) == 0)

        # TODO: test output

        myinput, outstream = StringIO(), StringIO()
        myinput.write(json.dumps({"residue" : residue,
                                  "messageText" : "biggroum pattern",
                                  "user" : "", "noteID" : "1"},))
        myinput.reset()
        self.assertTrue(main(TestScript.get_args("talk"),
                             myinput, outstream, biggroum_api_map) == 0)

        # TODO: test output


    def test_reaction(self):
        myinput, outstream = StringIO(), StringIO()
        myinput.write(json.dumps({}))
        myinput.reset()

        self.assertTrue(main(TestScript.get_args("reaction"), myinput, outstream,
                             biggroum_api_map) == 0)


class TestResidue(unittest.TestCase):
    def test_compilation_info(self):
        def test_res(residue, expected_residue, ci, fi):
            self.assertTrue(compare_json_obj(residue, expected_residue))
            self.assertTrue(compare_json_obj(Residue.get_compilation_infos(residue), ci))

            res_files = []
            for ci in Residue.get_compilation_infos(residue):
                res_files = res_files + Residue.get_files(ci)
            self.assertTrue(set(fi) == set(res_files))

        f1 = ["file1", "file2"]
        f2 = ["file3", "file4"]
        ci1 = {
            "cwd" : "cwd",
            "cmd" : "cmd",
            "args" : "args",
            "classpath" : "classpath",
            "files" : f1,
        }
        ci2 = copy.deepcopy(ci1)
        ci2["files"] = f2

        expected_residue = {"compilation_infos" : [ci1]}
        residue = Residue.append_compilation_info(None, ci1)
        test_res(residue, expected_residue, [ci1], f1)

        expected_residue = {"compilation_infos" : [ci1,ci2]}
        residue = Residue.append_compilation_info(residue, ci2)
        test_res(residue, expected_residue, [ci1,ci2], f1+f2)


    def test_anomaly(self):
        residue = Residue.store_anomaly(None, TestScript.ANOMALY1, "1")
        self.assertTrue(compare_json_obj(residue, {"anomalies" : {"1" : TestScript.ANOMALY1}}))

        residue = Residue.store_anomaly(residue, TestScript.ANOMALY2, "2")
        self.assertTrue(compare_json_obj(TestScript.ANOMALY1, Residue.retrieve_anomaly(residue, "1")))
        self.assertTrue(compare_json_obj(TestScript.ANOMALY2, Residue.retrieve_anomaly(residue, "2")))


class TestBash(unittest.TestCase):
    SCRIPTPATH = "biggroumcheck.sh"

    @unittest.skip("Skip, this must be fixed according to issue #64")
    def test_bash(self):
        previous = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        exec_file = os.path.join(previous, TestBash.SCRIPTPATH)

        my_env = os.environ.copy()
        my_env[GRAPH_EXTRACTOR_PATH] = get_extractor_path()
        my_env[FIXR_SEARCH_ENDPOINT] = "http://localhost:8081/process_muse_data"
        my_env["ENV_SETUP"] = "1"

        # Must fail, wrong command
        args = [exec_file, TestScript.FILEPATH, TestScript.COMMIT, "nothing"]
        proc = subprocess.Popen(args, cwd = previous,
                                stdin = subprocess.PIPE,
                                stdout = subprocess.PIPE,
                                stderr = subprocess.PIPE,
                                env = my_env)
        stdout, stderr = proc.communicate()
        self.assertTrue(proc.returncode == 1)

        # Must succeed on the run command
        script_input = {
            "residue" : {},
            "cwd" : "",
            "cmd" : "",
            "args" : "",
            "classpath" : [],
            "files" : ["file1.java", "file2.java"]
        }
        args = [exec_file, TestScript.FILEPATH, TestScript.COMMIT, "run"]
        proc = subprocess.Popen(args, cwd = previous,
                                stdin = subprocess.PIPE,
                                stdout = subprocess.PIPE,
                                stderr = subprocess.PIPE,
                                env = my_env)
        proc.stdin.write(json.dumps(script_input))
        stdout, stderr = proc.communicate()
        proc.stdin.close()
        self.assertTrue(proc.returncode == 0)

        compare_json_obj(json.loads(stdout),
                         {
                             "toolNotes" : [],
                             "residue" : {
                                 "compilation_infos" : script_input
                             }
                         }
        )
