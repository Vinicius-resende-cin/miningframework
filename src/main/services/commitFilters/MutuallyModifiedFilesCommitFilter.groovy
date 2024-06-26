package services.commitFilters

import interfaces.CommitFilter
import project.MergeCommit
import project.Project
import util.ProcessRunner
import app.MiningFramework

import java.util.stream.Collectors

class MutuallyModifiedFilesCommitFilter implements CommitFilter {

    @Override
    boolean applyFilter(Project project, MergeCommit mergeCommit) {
        List<String> leftFilePaths = getModifiedFilePaths(project, mergeCommit, mergeCommit.getLeftSHA())
        List<String> rightFilePaths = getModifiedFilePaths(project, mergeCommit, mergeCommit.getRightSHA())
        return !leftFilePaths.disjoint(rightFilePaths)
    }

    static List<String> getModifiedFilePaths(Project project, MergeCommit mergeCommit, String commitSHA) {
        List<String> parameters = [ 'git', 'diff-tree', '--no-commit-id', '--name-status', '-r' ]
        parameters.addAll(mergeCommit.getAncestorSHA(), commitSHA)

        ProcessBuilder processBuilder = ProcessRunner.buildProcess(project.getPath())
        processBuilder.command().addAll(parameters)

        Process process = ProcessRunner.startProcess(processBuilder)
        List<String> files = process.getInputStream().readLines()

        return files.stream()
            .filter(line -> MutuallyModifiedFilesCommitFilter::isModifiedFile(getFileStatus(line)))
            .map(MutuallyModifiedFilesCommitFilter::getFilePath)
            .filter(MutuallyModifiedFilesCommitFilter::isExpectedFileExtension)
            .collect(Collectors.toList())
    }

    private static char getFileStatus(String diffTreeOutputLine) {
        return diffTreeOutputLine.charAt(0)
    }

    private static boolean isModifiedFile(char fileStatus) {
        return fileStatus == 'M'
    }

    private static String getFilePath(String diffTreeOutputLine) {
        return diffTreeOutputLine.substring(1).trim()
    }

    private static boolean isExpectedFileExtension(String filePath) {
        return filePath.endsWith(MiningFramework.arguments.getFileExtension())
    }

}