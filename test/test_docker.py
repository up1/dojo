from test.support.common import *


def clean_up_docker_container():
    run_shell('docker ps -a -q --filter "name=testdojorunid" | xargs --no-run-if-empty docker stop')
    run_shell('docker ps -a -q --filter "name=testdojorunid" | xargs --no-run-if-empty docker rm')


def test_docker_container_is_removed():
    result = run_command('docker', ['ps', '-a', '--filter', "name=testdojorunid"])
    assert not 'testdojorunid' in result.stderr
    assert result.returncode == 0


def test_docker_when_zero_exit():
    clean_up_docker_container()
    result = run_dojo('--debug=true --test=true --image=alpine:3.8 whoami'.split(' '))
    assert 'Dojo version' in result.stderr
    assert 'root' in result.stdout
    assert 'alpine:3.8 whoami' in result.stderr
    assert 'Exit status from run command: 0' in result.stderr
    assert 'Exit status from cleaning: 0' in result.stderr
    assert 'Exit status from signals: 0' in result.stderr
    assert_no_warnings_or_errors(result.stderr)
    assert_no_warnings_or_errors(result.stdout)
    assert result.returncode == 0
    test_docker_container_is_removed()


def test_docker_capture_output():
    clean_up_docker_container()
    result = run_dojo(['--debug=true', '--test=true', '--image=alpine:3.8', 'sh', '-c', "printenv HOME"])
    assert 'Dojo version' in result.stderr
    assert '/root\n' == result.stdout
    assert 'Exit status from run command: 0' in result.stderr
    assert 'Exit status from cleaning: 0' in result.stderr
    assert 'Exit status from signals: 0' in result.stderr
    assert_no_warnings_or_errors(result.stderr)
    assert_no_warnings_or_errors(result.stdout)
    assert result.returncode == 0
    test_docker_container_is_removed()


def test_docker_when_non_existent_command():
    clean_up_docker_container()
    result = run_dojo('--debug=true --test=true --image=alpine:3.8 notexistentcommand'.split(' '))
    assert 'Dojo version' in result.stderr
    assert 'executable file not found' in result.stderr
    assert 'Exit status from run command: 127' in result.stderr
    assert_no_warnings_or_errors(result.stdout)
    assert result.returncode == 127
    test_docker_container_is_removed()


def test_docker_when_no_command():
    clean_up_docker_container()
    result = run_dojo('--debug=true --test=true --image=alpine:3.8 -i=false'.split(' '))
    assert 'Dojo version' in result.stderr
    assert 'Exit status from run command: 0' in result.stderr
    assert 'Exit status from cleaning: 0' in result.stderr
    assert 'Exit status from signals: 0' in result.stderr
    assert_no_warnings_or_errors(result.stderr)
    assert_no_warnings_or_errors(result.stdout)
    assert result.returncode == 0
    test_docker_container_is_removed()


def test_docker_when_double_dash_command_split():
    clean_up_docker_container()
    result = run_dojo('--debug=true --test=true --image=alpine:3.8 -- whoami'.split(' '))
    assert 'Dojo version' in result.stderr
    assert 'root' in result.stdout
    assert 'alpine:3.8 whoami' in result.stderr
    assert 'Exit status from run command: 0' in result.stderr
    assert 'Exit status from cleaning: 0' in result.stderr
    assert 'Exit status from signals: 0' in result.stderr
    assert_no_warnings_or_errors(result.stderr)
    assert_no_warnings_or_errors(result.stdout)
    assert result.returncode == 0
    test_docker_container_is_removed()


def test_docker_when_shell_command():
    clean_up_docker_container()
    result = run_dojo(['--debug=true', '--test=true', '--image=alpine:3.8', 'sh', '-c', 'echo hello'])
    assert 'Dojo version' in result.stderr
    assert 'hello' in result.stdout
    assert 'Exit status from run command: 0' in result.stderr
    assert 'Exit status from cleaning: 0' in result.stderr
    assert 'Exit status from signals: 0' in result.stderr
    assert_no_warnings_or_errors(result.stderr)
    assert_no_warnings_or_errors(result.stdout)
    assert result.returncode == 0
    test_docker_container_is_removed()


def test_docker_preserves_env_vars():
    clean_up_docker_container()
    envs = dict(os.environ)
    envs['ABC'] = 'custom_value'
    result = run_dojo(
        ['--debug=true', '--test=true', '--image=alpine:3.8', 'sh', '-c', 'env | grep ABC'],
        env=envs)
    assert 'Dojo version' in result.stderr
    assert 'custom_value' in result.stdout
    assert 'Exit status from run command: 0' in result.stderr
    assert_no_warnings_or_errors(result.stderr)
    assert_no_warnings_or_errors(result.stdout)
    assert result.returncode == 0


def test_docker_preserves_multiline_env_vars():
    clean_up_docker_container()
    envs = dict(os.environ)
    envs['ABC'] = """first line
second line"""
    result = run_dojo(
        ['--debug=true', '--test=true', '--image=alpine:3.8', 'sh', '-c', '"source /etc/dojo.d/variables/00-multiline-vars.sh && env | grep -A 1 ABC"'],
        env=envs)
    assert 'Dojo version' in result.stderr
    assert '/etc/dojo.d/variables/00-multiline-vars.sh' in result.stderr
    assert_no_warnings_or_errors(result.stderr)
    assert_no_warnings_or_errors(result.stdout)
    assert result.returncode == 0
    assert 'Exit status from run command:' in result.stderr
    assert """first line
second line""" in result.stdout


def test_docker_when_custom_relative_directory():
    clean_up_docker_container()
    result = run_dojo(['-c', 'test/test-files/Dojofile', '--debug=true', '--test=true', '--image=alpine:3.8', 'whoami'])
    assert 'Dojo version' in result.stderr
    assert 'root' in result.stdout
    assert 'Exit status from run command: 0' in result.stderr
    assert 'Exit status from cleaning: 0' in result.stderr
    assert 'Exit status from signals: 0' in result.stderr
    assert_no_warnings_or_errors(result.stderr)
    assert_no_warnings_or_errors(result.stdout)
    assert result.returncode == 0
    test_docker_container_is_removed()


def test_docker_when_nonexistent_custom_relative_directory():
    clean_up_docker_container()
    try:
        os.removedirs(os.path.join(project_root, 'test/test-files/not-existent'))
    except FileNotFoundError:
        pass
    result = run_dojo(['-c', 'test/test-files/Dojofile.work_not_exists', '--debug=true', '--test=true', '--image=alpine:3.8', 'whoami'])
    assert 'Dojo version' in result.stderr
    assert 'root' in result.stdout
    assert "test/test-files/not-existent does not exist" in result.stderr
    assert 'WARN' in result.stderr
    assert 'Exit status from run command: 0' in result.stderr
    assert 'Exit status from cleaning: 0' in result.stderr
    assert 'Exit status from signals: 0' in result.stderr
    assert result.returncode == 0
    test_docker_container_is_removed()


def test_docker_pull():
    result = run_dojo('--debug=true --action=pull --image=alpine:3.8'.split(' '))
    assert "Dojo version" in result.stderr
    assert "Pulling from library/alpine" in result.stdout
    assert result.returncode == 0
    assert_no_warnings_or_errors(result.stderr)
    assert_no_warnings_or_errors(result.stdout)