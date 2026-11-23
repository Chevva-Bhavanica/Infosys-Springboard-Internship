
from agents.log_analysis_agent import analyze_logs


def test_python_exception():

    result = analyze_logs({
        "title": "Login failure",
        "description": "Application crashes during login",
        "stack_trace": '''
Traceback (most recent call last):
  File "app.py", line 25, in login
    user = get_user()
  File "database.py", line 40, in get_user
    raise ValueError("Invalid user")
ValueError: Invalid user
'''
    })

    assert result.exception_type == "ValueError"
    assert result.error_message == "Invalid user"
    assert result.failure_file == "app.py"
    assert result.line_number == 25


def test_java_exception():

    result = analyze_logs({
        "stack_trace": '''
java.lang.NullPointerException: Cannot invoke method
    at com.example.LoginService.authenticate(LoginService.java:45)
    at com.example.LoginController.login(LoginController.java:20)
'''
    })

    assert result.exception_type == "java.lang.NullPointerException"
    assert result.failure_file == "LoginService.java"
    assert result.line_number == 45


def test_node_exception():

    result = analyze_logs({
        "error_logs": '''
TypeError: Cannot read properties of undefined
    at loginUser (C:\\app\\auth.js:18:12)
'''
    })

    assert result.exception_type == "TypeError"
    assert result.failure_file == "C:\\app\\auth.js"
    assert result.line_number == 18


def test_missing_stack_trace():

    result = analyze_logs({
        "title": "Application issue",
        "description": "Application is not responding"
    })

    assert result.failure_file is None
    assert result.line_number is None
    assert "Recognizable stack frame" in result.missing_information
