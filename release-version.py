#!/usr/bin/env python3
import subprocess
import os
import shutil
import glob
import click
from os import path


def run_script(script, stdin=None):
    """Returns (stdout, stderr), raises error on non-zero return code"""
    # Note: by using a list here (['bash', ...]) you avoid quoting issues, as the
    # arguments are passed in exactly this order (spaces, quotes, and newlines won't
    # cause problems):
    proc = subprocess.Popen(['bash', '-c', script],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if proc.returncode:
        print("script error")
        print(script)
        print(proc.returncode)
        raise ScriptException(proc.returncode, stdout, stderr, script)
    return stdout, stderr


class ScriptException(Exception):
    def __init__(self, returncode, stdout, stderr, script):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        Exception.__init__('Error in script')


def sync_to_s3(aar_release_name, sdk_version):
    os.chdir('release-folder/')
    print('Updating maven with the new binaries')
    output, err = run_script(
        'mvn install:install-file -DgroupId=net.singular.segment.integration -DartifactId=singular_segment_sdk -DcreateChecksum=true -Dversion={0} -Dpackaging=aar -Dfile={1} -DpomFile=../segment-singular-android/generated-sdk.pom -DlocalRepositoryPath=.'.format(
            sdk_version, aar_release_name))
    #os.rename('./net/singular/segment/integration/singular_segment_sdk/maven-metadata-local.xml',
    #          './net/singular/segment/integration/singular_segment_sdk/')
    os.remove(aar_release_name)
    for filename in glob.iglob(os.getcwd() + '/**/*', recursive=True):
        if filename.endswith('.DS_Store'):
            os.remove(filename)
        elif filename.endswith('.git'):
            os.rmtree(filename)
    print('Syncing the new version to S3')
    output, err = run_script('s3cmd sync -P . s3://maven.singular.net')
    os.chdir('../')


def download_sdk_tools():
    repo_path = 'sdk-tools/'
    if path.exists(repo_path):
        os.chdir(repo_path)
        os.system("git reset --hard")
        os.system("git clean -fxd")
        os.system("git checkout master")
        os.system("git pull")
        os.chdir("../")
    else:
        os.system("git clone git@github.com:singular-labs/{0}.git".format(repo_path.replace('/', '')))

    os.system("chmod +xwr ./sdk-tools/update_zendesk_articles.py")


def update_docs():
    print("Updating documentation")
    platform = "android"
    output, err = run_script("git describe --abbrev=0 --tags `git rev-list --tags --skip=1  --max-count=1`")
    old_version = output.decode('utf-8').strip()
    output, err = run_script("git describe --tags --abbrev=0")
    new_version = output.decode('utf-8').strip()
    os.chdir('sdk-tools/')
    command = "./update_zendesk_articles.py --platform={0} --old-version={1} --new-version={2}".format(platform, old_version.replace('v', ''), new_version.replace('v', ''))
    os.system(command)


@click.command()
@click.option('-dry', is_flag=True, help='Dry run will build the SDK but will not sync to S3')
@click.option('-name', default=None, help='Change the name of the SDK. only works on dry runs')
def build_android_sdk(dry, name):
    release_folder = 'release-folder'
    if os.path.exists(release_folder):
        shutil.rmtree(release_folder)

    sdk_name = 'Singular'

    if name is not None:
        if not dry:
            print("Custom SDK name works only in dry mode")
            return

        sdk_name = name

    print('Building the SDK...')
    output, err = run_script('./gradlew -q segment-singular-android:makeJarRelease')
    output, err = run_script('./gradlew -q segment-singular-android:getReleaseJarName | grep "aar"')
    aar_name = output.decode('utf-8').strip()
    sdk_version = aar_name.split('-')[1].replace('v', '')

    aar_release_name = '{0}-v{1}.aar'.format(sdk_name, sdk_version)

    print('Generating new pom file')

    output, err = run_script('./gradlew -q segment-singular-android:generatePomFile')

    os.mkdir('release-folder')
    shutil.copyfile('segment-singular-android/build/outputs/aar/' + aar_name,
                    "{0}/{1}".format(release_folder, aar_release_name))

    if not dry:
        sync_to_s3(aar_release_name, sdk_version)
    #    download_sdk_tools()
    #    update_docs()

    print('Done!')


if __name__ == '__main__':
    build_android_sdk()
