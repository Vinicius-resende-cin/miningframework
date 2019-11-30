# This script receives as input the path to a framework input file, the path to a directory generated by the miningframework and a github acess token, it downloads the release files from github and moves the files to the directory passed as input.


import sys
import requests
import json
import subprocess
import time
import shutil
import os

PATH = "path"
NAME = "name"
RESULT = "result"
GITHUB_API= "https://api.github.com"
TRAVIS_API = "https://api.travis-ci.org"
LOGIN = "login"
DOWNLOAD_URL='browser_download_url'
ASSETS="assets"
MESSAGE_PREFIX="Trigger build #"
RELEASE_PREFIX= "fetchjar-"

inputPath = sys.argv[1] # input path passed as cli argument
outputPath = sys.argv[2] # output path passed as cli argument
token = sys.argv[3] # token passed as cli argument

def fetchJars(inputPath, outputPath, token):
    # this method reads a csv input file, with the projects name and path
    # for each project it downloads the build generated via github releases
    # and moves the builds to the output generated by the framework
    
    print("Starting build collection")

    tokenUser = get_github_user(token)[LOGIN]

    parsedInput = read_input(inputPath)
    parsedOutput = read_output(outputPath)
    newResultsFile = []

    for project in parsedInput:

        splitedProjectPath = project[PATH].split('/')
        projectName = splitedProjectPath[len(splitedProjectPath) - 1]
        githubProject = tokenUser + '/' + projectName
        print (projectName)        

        get_builds_and_wait(githubProject)

        releases = get_github_releases(token, githubProject)

        # download the releases for the project moving them to the output directories
        for release in releases:
            # check if release was generated by the framework
            if (release[NAME].startswith(RELEASE_PREFIX)):
                commitSHA = release[NAME].replace(RELEASE_PREFIX, '')
                print ("Downloading " + commitSHA )
                try:
                    downloadPath = mount_download_path(outputPath, project, commitSHA)
                    downloadUrl = release[ASSETS][0][DOWNLOAD_URL]
                    download_file(downloadUrl, downloadPath)
                    if (commitSHA in parsedOutput):
                        newResultsFile.append(parsedOutput[commitSHA])
                        untar_and_remove_file(downloadPath)
                    print (downloadPath + ' is ready')
                except:
                    pass
    
        remove_commit_files_without_builds (outputPath, projectName)
      
    with open(outputPath + "/data/results-with-builds.csv", 'w') as outputFile:
        outputFile.write("project;merge commit;className;method;left modifications;left deletions;right modifications;right deletions\n")
        outputFile.write("\n".join(newResultsFile))
        outputFile.close()

def read_output(outputPath):
    fo = open(outputPath + "/data/results.csv")
    file = fo.read()
    fo.close()

    fileOutLines = file.split("\n")
    return parse_output(fileOutLines)

def parse_output(lines):
    result = {}
    for line in lines[1:]:
        cells = line.split(";")
        if (len (cells) > 1):
            result[cells[1]] = line
    return result

def read_input(inputPath):
    f = open(inputPath, "r")
    file = f.read()
    f.close()

    bruteLines = file.split("\n")
    return parse_input(bruteLines)

def parse_input(lines):
    # parse framework input csv file 
    result = []
    for line in lines[1:]:
        cells = line.split(",")
        if (len (cells) > 1):
            method = {}
            method[NAME] = cells[0]
            method[PATH] = cells[1]
            result.append(method)
    return result

def download_file(url, target_path):
    # download file from url
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(target_path, 'wb') as f:
            f.write(response.raw.read())

def mount_download_path(outputPath, project, commitSHA):
    # mount path where the downloaded build will be moved to
    return outputPath + '/files/' + project[NAME] + '/' + commitSHA + '/result.tar.gz'

def untar_and_remove_file(downloadPath): 
    downloadDir = downloadPath.replace('result.tar.gz', '')
    subprocess.call(['mkdir', downloadDir + 'build'])
    subprocess.call(['tar', '-xf', downloadPath, '-C', downloadDir + '/build', ])
    subprocess.call(['rm', downloadPath])

def get_builds_and_wait(project):
    has_pendent = True
    filtered_builds = []
    while (has_pendent):
        builds = get_travis_project_builds(project)
        filtered_builds = filter (lambda x: not x["branch"].startswith("untagged"), builds)
        
        has_pendent = False
        for build in filtered_builds:
            print (build["state"])
            has_pendent = has_pendent or (build["state"] != "finished")
    
        if (has_pendent):
            print ("Waiting 30 seconds")
            time.sleep(30)

    return filtered_builds


def get_travis_project_builds(project):
    return requests.get(TRAVIS_API + '/repos/' + project + '/builds').json()

def get_github_user(token):
    return requests.get(GITHUB_API + '/user', headers=get_headers(token)).json()

def get_github_releases(token, project):
    return requests.get(GITHUB_API + '/repos/' + project + '/releases', headers=get_headers(token)).json()

def get_headers(token):
    return {
        "Authorization": "token " + token
    }


def remove_commit_files_without_builds (outputPath, projectName):
    files_path = outputPath + "/files/" + projectName +  "/"

    if (os.path.exists(files_path)): 
        commit_dirs = os.listdir(files_path)

        for directory in commit_dirs:
            commit_dir = files_path + directory
            build_dir = commit_dir + "/build"

            if (not os.path.exists(build_dir)):
                shutil.rmtree(commit_dir)

        if (len (os.listdir(files_path)) == 0 ):
            shutil.rmtree(files_path)

fetchJars(inputPath, outputPath, token)