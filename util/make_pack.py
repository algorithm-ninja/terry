#!/usr/bin/env python3

import tempfile

import argparse
import os.path
import shutil
import subprocess


def main(args):
    task_names = [os.path.basename(task) for task in args.task_dir]
    with tempfile.TemporaryDirectory() as workdir:
        shutil.copytree(args.__users__, os.path.join(workdir, "__users__"))
        for task in args.task_dir:
            target_dir = os.path.join(workdir, os.path.basename(task))
            shutil.copytree(task, target_dir, dirs_exist_ok=True)
            if args.task_maker:
                print("Building task", task)
                subprocess.run(
                    ["task-maker", "--ui=silent",
                     "--task-dir=" + target_dir, "do_not_evaluate"])
            shutil.rmtree(os.path.join(target_dir, "solutions"), True)

        extra_files = []
        if args.tutorials:
            tutorials = os.path.abspath(args.tutorials)
            extra_files += ["tutorials"]
            shutil.copytree(tutorials, os.path.join(workdir, "tutorials"))

        subprocess.run(["zip", "-r", "pack.zip", "__users__"] + task_names + extra_files,
                       cwd=workdir)
        subprocess.run(
            ["terr-crypt-file", "--metadata", args.metadata, args.password,
             os.path.join(workdir, "pack.zip"), args.output])

    if not args.skip_check:
        sanity_check = os.path.join(os.path.dirname(__file__), "sanity_checks",
                                    "pack_sanity_check.py")
        subprocess.run([sanity_check, "--fuzz", args.output, args.password,
                        ",".join(task_names)])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-maker", help="Builda i task usando task-maker (deprecated)",
                        action="store_true")
    parser.add_argument("--skip-check", help="Skippa il check del pack",
                        action="store_true")
    parser.add_argument("--both-arch", help="Compila i manager anche per x86-64 (deprecated)",
                        action="store_true")
    parser.add_argument("--tutorials", help="Cartella da aggiungere al pack con i tutorial",
                        action="store")
    parser.add_argument("password",
                        help="Password da usare per cifrare il pack")
    parser.add_argument("metadata", help="Metadati da includere nel pack")
    parser.add_argument("output", help="Percorso del file di output")
    parser.add_argument("__users__",
                        help="Cartella con i contest.yaml (__users__)")
    parser.add_argument("task_dir", help="Cartella con un task", nargs="+")
    main(parser.parse_args())
