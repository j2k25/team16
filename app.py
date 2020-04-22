from __future__ import print_function
import re
import MySQLdb
import MySQLdb.cursors
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL

app = Flask(__name__)

app.secret_key = 'hotdog'

app.config['MYSQL_HOST'] = 'rtzsaka6vivj2zp1.cbetxkdyhwsb.us-east-1.rds.amazonaws.com'
app.config['MYSQL_USER'] = 'yukolhm10l2bxf76'
app.config['MYSQL_PASSWORD'] = 'ondoxpul1ezwcq9w'
app.config['MYSQL_DB'] = 'bjbx4fmvqoqiij60'

# Initialize MySQL
mysql = MySQL(app)

# http://localhost:5000/pythonlogin/ - this will be the login page, we need to use both GET and POST requests


@app.route('/', methods=['GET', 'POST'])
def login():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT e.id, department_name, dept_id, name, username, password, is_manager, log_in, log_out, '
                       'total_session_time, total_login, hourly_wage FROM employee_accounts e join department d '
                       'on e.dept_id = d.id WHERE username = %s AND password = %s', (username, password,))
        # Fetch one record and return result
        account = cursor.fetchone()
        print(account)
        # If account exists in accounts table in our database
        if account:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = account['id']
            session['name'] = account['name']
            session['username'] = account['username']
            session['password'] = account['password']
            session['dept_id'] = account['dept_id']
            session['department_name'] = account['department_name']
            session['is_manager'] = account['is_manager']
            session['clocked_in'] = False
            cursor.execute('update employee_accounts SET `log_in` = current_timestamp() WHERE  id = %s', (session['id'],))
            mysql.connection.commit()
            if session['is_manager'] == 1:
                # Redirect to manager home page
                return redirect(url_for('manager_home'))
            else:
                if session['is_manager'] == 0:
                    # Redirect to employee home page
                    return redirect(url_for('employee_home'))
        else:
            # Account doesnt exist or username/password incorrect
            msg = 'Incorrect username/password!'
    # Show the login form with message (if any)
    return render_template('index.html', msg=msg)


@app.route('/timestamp')
def timestamp():
    # Check if user is loggedin
    if 'loggedin' in session:
        return render_template('timestamp.html')
    else:
        return redirect(url_for('login'))


# http://localhost:5000/python/logout - this will be the logout page
@app.route('/logout')
def logout():
    if session['clocked_in'] is True:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('update assigned SET `clock_out` = current_timestamp() WHERE  id = %s and'
                       '`employee_account_id` = %s', (session['ass_id'], session['id'],))
        mysql.connection.commit()
        session['clocked_in'] = False
# select addtime(current_time(), sec_to_time(timestampdiff(second, '2020-04-20 19:52:28', '2020-04-20 19:52:41')));
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('update employee_accounts SET `log_out` = current_timestamp() WHERE  id = %s', (session['id'],))
    mysql.connection.commit()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('update employee_accounts set `total_session_time` = sec_to_time(timestampdiff(second, `log_in`,`log_out`)) '
                   'where id = %s', (session['id'],))
    mysql.connection.commit()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('update employee_accounts set `total_login` = addtime(`total_login`,`total_session_time`) '
                   'where id = %s', (session['id'],))
    mysql.connection.commit()
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    # Redirect to login page
    return redirect(url_for('login'))


# http://localhost:5000/pythinlogin/home - this will be the home page, only accessible for loggedin users


@app.route('/home')
def home():
    # Check if user is loggedin
    if 'loggedin' in session:
        if session['is_manager'] == 1:
            return redirect(url_for('manager_home'))
        else:
            if session['is_manager'] == 0:
                return redirect(url_for('employee_home'))
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/employee_home')
def employee_home():
    # Check if user is loggedin
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employee_accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        assign_list = []
        cursor.execute('SELECT * FROM assigned WHERE employee_account_id = %s', (session['id'],))
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            assign_list.append(row)
        # User is loggedin show them the employee home page
        return render_template('employee_home.html', account=account, list=assign_list)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/manager_home')
def manager_home():
    # Check if user is loggedin
    session['valid_project'] = False
    session['valid_task'] = False
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employee_accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        project_list = []
        cursor.execute('SELECT p.id, project_name, project_description, department_id, department_name, '
                       'planned_start_date, planned_end_date, planned_budget, actual_start_date, actual_start_date, actual_end_date, '
                       'actual_budget, status_on_tasks FROM project p join department d on p.department_id = d.id')
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            if row['status_on_tasks']:
                row['status_on_tasks'] = float(row['status_on_tasks'])*100
            project_list.append(row)
        assign_list = []
        cursor.execute('SELECT * FROM assigned WHERE employee_account_id = %s', (session['id'],))
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            assign_list.append(row)
        # User is loggedin show them the employee home page
        return render_template('manager_home.html', account=account, list=project_list, list2=assign_list)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


# http://localhost:5000/pythinlogin/profile - this will be the profile page, only accessible for loggedin users


@app.route('/profile')
def profile():
    # Check if user is loggedin
    session['valid_project'] = False
    session['valid_task'] = False
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employee_accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', account=account)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/reports')
def reports():
    # Check if user is loggedin
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employee_accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        if account['is_manager'] == 1:
            # Show the manager profile page with account info
            return redirect(url_for('manager_reports'))
        else:
            if session['is_manager'] == 0:
                # Show the employee profile page with account info
                return redirect(url_for('employee_reports'))
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/employee_reports')
def employee_reports():
    # Check if user is loggedin
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employee_accounts WHERE id = %s', (session['id'],))
        assigned = cursor.fetchone()
        assignment2 = []
        cursor.execute('SELECT * FROM assigned WHERE employee_account_id = %s', (session['id'],))
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            assignment2.append(row)
            print(row)
        # User is loggedin show them the home page
        return render_template('employee_reports.html', account=assigned, list=assignment2)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/manager_reports')
def manager_reports():
    # Check if user is loggedin
    session['valid_project'] = False
    session['valid_task'] = False
    if 'loggedin' in session:
        # User is loggedin show them the report page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employee_accounts WHERE id = %s', (session['id'],))
        employee_accounts = cursor.fetchone()
        return render_template('manager_reports.html', account=employee_accounts)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/chartdb', methods=['GET', 'POST'])
def chartdb():
    if request.method == 'POST' and 'timeframe' in request.form:
        # We need all the account info for the user so we can display it on the profile page
        updatecount = 0
        insertcount = 0
        deletecount = 0
        value = int(request.form['timeframe'])
        method = request.form['method']
        print(value)
        print(method)
        time = 0
        if method == 'h':
            m = 10000
        if method == 'd':
            m = 240000
        if method == 'm':
            m = 7320000
        time = value * m
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * from change_log where change_date >= subtime(current_timestamp(), %s) and update_type = %s',(time,'UPDATE',))
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            updatecount = updatecount + 1
            print(row)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * from change_log where change_date >= subtime(current_timestamp(), %s) and update_type = %s',(time,'INSERT',))
        while True:
            row2 = cursor.fetchone()
            if row2 is None:
                break
            insertcount = insertcount + 1
            print(row)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * from change_log where change_date >= subtime(current_timestamp(), %s) and update_type = %s',(time,'DELETE',))
        while True:
            row3 = cursor.fetchone()
            if row3 is None:
                break
            deletecount = deletecount + 1
            print(row)

        assignment2 = []
        # cursor.execute('SELECT * FROM change_log ORDER BY id DESC')
        cursor.execute(
            'SELECT * from change_log where change_date >= subtime(current_timestamp(), %s) ORDER BY id DESC',(time,))
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            assignment2.append(row)
            print(row)
        # User is loggedin show them the home page
        return render_template('chartdb.html', updatetrack=updatecount, inserttrack=insertcount, deletetrack=deletecount, list=assignment2)
    if 'loggedin' in session:
        return render_template('chartinput.html')
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/chartproject', methods=['GET', 'POST'])
def chartproject():
    msg =''
    if request.method == 'POST' and 'project_id' in request.form:
        # We need all the account info for the user so we can display it on the profile page
        project_id = request.form['project_id']
        department_no = 0
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM project WHERE id = %s', (project_id,))
        account = cursor.fetchone()
        if account:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * from project where id = %s', (project_id,))
            pulled = cursor.fetchone()
            planned = pulled['planned_budget']
            actual = pulled['actual_budget']
            department = pulled['department_id']
            print(planned)
            print(actual)
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * from department where id = %s', (department,))
            pulled = cursor.fetchone()
            dpt = pulled['department_name']
            print(dpt)

            return render_template('chartproject.html', plannedbudget=planned, actualbudget=actual, departmentname=dpt)

        else:
            msg = 'No project with that ID exists'
            return render_template('chartinputproject.html', msg=msg)

    if 'loggedin' in session:
        return render_template('chartinputproject.html', msg=msg)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/chartdepartment', methods=['GET', 'POST'])
def chartdepartment():
    msg =''
    if request.method == 'POST' and 'department_id' in request.form:
        # We need all the account info for the user so we can display it on the profile page
        department_id = request.form['department_id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM department WHERE id = %s', (department_id,))
        account = cursor.fetchone()
        if account:

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * from department where id = %s', (department_id,))
            pulled = cursor.fetchone()
            dpt = pulled['department_name']

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('select (select sum(time_to_sec(total_time)) FROM (SELECT e.name, e.total_login, a.id, a.task_id,'
                           ' a.employee_account_id, a.total_time, t.project_id, p.department_id from employee_accounts e join'
                           ' assigned a on e.id = a.employee_account_id join task t on a.task_id'
                           ' = t.id join project p on t.project_id = p.id where department_id = %s) q1)',(department_id,))
            pulled = cursor.fetchone()
            efficient = float(pulled['(select sum(time_to_sec(total_time)) FROM (SELECT e.name,'
                                     ' e.total_login, a.id, a.task_id, a.employee_account_id, a.total_time, t.project_id, p.'
                                     'department_id from employee_accounts e join assigned a on e.id = a.employee_account_id jo'
                                     'in task t on a.task_id ='])

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            cursor.execute('select sum(time_to_sec(total_login)) from (SELECT e.name, e.total_login, a.id, a.task_id,'
                           ' a.employee_account_id, a.total_time, t.project_id, p.department_id from employee_accounts e join'
                           ' assigned a on e.id = a.employee_account_id join task t on a.task_id = t.id join project p '
                           'on t.project_id = p.id where department_id = %s) q2',(department_id,))
            pulled = cursor.fetchone()
            divisor = float(pulled['sum(time_to_sec(total_login))'])
            eff = efficient / divisor
            unused = (divisor-efficient) / divisor

            hours = round((efficient / 3600), 2)


            return render_template('chartdepartment.html', efficiency=eff, not_utilized=unused, departmentname=dpt, departmenthours=hours)

        else:
            msg = 'No department with that ID exists'
            return render_template('chartinputdepartment.html', msg=msg)

    if 'loggedin' in session:
        return render_template('chartinputdepartment.html', msg=msg)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/chartdepartmentcompare', methods=['GET', 'POST'])
def chartdepartmentcompare():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        assignment2 = []
        # cursor.execute('SELECT * FROM change_log ORDER BY id DESC')
        cursor.execute(
            'SELECT * from department')
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            assignment2.append(row)
            print(row)
        # User is loggedin show them the home page
        return render_template('chartdepartmentcompare.html', list=assignment2)
    else:
        # User is not loggedin redirect to login page
        return redirect(url_for('login'))


@app.route('/projectreport', methods=['GET', 'POST'])
def projectreport():
    msg =''
    if request.method == 'POST' and 'project_id' in request.form:
        # We need all the account info for the user so we can display it on the profile page
        project_id = request.form['project_id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM project WHERE id = %s', (project_id,))
        account = cursor.fetchone()
        if account:

            assignment2 = []
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * from warnings_on_projects where project_id = %s', (project_id,))
            while True:
                row = cursor.fetchone()
                if row is None:
                    break
                assignment2.append(row)
                print(row)
            if not assignment2:
                msg = 'Project with that ID does not have any warnings'
                return render_template('projectreport.html', msg=msg)

            return render_template('projectreport.html', list=assignment2)
        else:
            msg = 'No project with that ID exists'
            return render_template('projectinput.html', msg=msg)

    if request.method == 'POST' and 'warning_id' in request.form:
        # We need all the account info for the user so we can display it on the profile page
        warning_id = request.form['warning_id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM warnings_on_projects WHERE id = %s', (warning_id,))
        account = cursor.fetchone()
        if account:

            deletestate = "DELETE FROM warnings_on_projects WHERE id = %s"
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(deletestate, (warning_id,))
            mysql.connection.commit()

            msg = 'You have successfully deleted a warning!'
            return render_template('projectreport.html', msg=msg)
        else:
            msg = 'No project with that ID exists'
            return render_template('projectinput.html', msg=msg)
    if 'loggedin' in session:
        return render_template('projectinput.html', msg=msg)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/assignments', methods=['GET', 'POST'])
def assignments():
    # Check if user is loggedin
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employee_accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        if request.method == 'POST' and 'assigned_id' in request.form:
            # Create variables for easy access
            assigned_id = request.form['assigned_id']
            # Check if assignment exists using MySQL
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM assigned where id = %s and employee_account_id = %s', (assigned_id,
                                                                                                 session['id'],))
            # Fetch and return results
            results = cursor.fetchone()
            print(results)
            if results:
                if session['clocked_in'] is True:
                    if int(assigned_id) != int(session['ass_id']):
                        print(session['ass_id'], assigned_id)
                        msg = 'The assignment id you have entered does not match your current clocked in session. ' \
                              'Please re-enter a valid assignment id: '
                        return render_template('assignments.html', msg=msg)
                    cursor.execute('update assigned SET `clock_out` = current_timestamp() WHERE  id = %s and'
                                   '`employee_account_id` = %s', (assigned_id, session['id'],))
                    mysql.connection.commit()
                    session['clocked_in'] = False
                    msg = 'You have successfully clocked out'
# select addtime(current_time(), sec_to_time(timestampdiff(second, '2020-04-20 19:52:28', '2020-04-20 19:52:41')));
                    cursor.execute('update assigned SET `total_time` = addtime(`total_time`, '
                                   'sec_to_time(timestampdiff(second, `clock_in`, `clock_out`))) WHERE `id` = %s',
                                   (assigned_id,))
                    mysql.connection.commit()
                    return render_template('assignments.html', account=account, msg=msg, session=session)
                else:
                    if session['clocked_in'] is False:
                        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                        cursor.execute('update assigned SET `clock_in` = current_timestamp() WHERE  id = %s and'
                                       '`employee_account_id` = %s', (assigned_id, session['id'],))
                        mysql.connection.commit()
                        session['clocked_in'] = True
                        session['ass_id'] = results['id']
#                        session['task_id'] = results['task_id']
#                        session['total_time'] = str(results['total_time'])
                        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                        cursor.execute('select t.id, task_name, description, project_id, planned_start_date, '
                                       'planned_end_date, planned_budget, actual_start_date, actual_end_date, '
                                       'actual_budget from task t join assigned a on t.id = a.task_id where '
                                       'a.id = %s and a.employee_account_id = %s', (assigned_id, session['id'],))
                        task_info = cursor.fetchone()
                        print(task_info)
                        session['t_id'] = task_info['id']
                        session['task_name'] = task_info['task_name']
                        session['description'] = task_info['description']
                        session['project_id'] = task_info['project_id']
                        session['planned_start_date'] = task_info['planned_start_date']
                        session['planned_end_date'] = task_info['planned_end_date']
                        session['planned_budget'] = str(task_info['planned_budget'])
                        session['actual_start_date'] = task_info['actual_start_date']
                        session['actual_end_date'] = task_info['actual_end_date']
                        session['actual_budget'] = str(task_info['actual_budget'])
                        msg = 'You have successfully clocked in'
                        return render_template('assignments.html', account=account, msg=msg, session=session)
        else:
            msg = 'Please enter a valid assignment id: '
            return render_template('assignments.html', account=account, msg=msg)
    # User has entered a assign id that doesnt exist // User is not loggedin redirect to login page
    msg = 'Either the assignment id does not exist or is not assigned to you. Please re-enter a valid assignment id: '
    return render_template('assignments.html', msg=msg)


@app.route('/tasks', methods=['GET', 'POST'])
def tasks():
    # Check if user is loggedin
    session['valid_task'] = False
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employee_accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        if request.method == 'POST' and 'task_id' in request.form:
            # Create variables for easy access
            task_id = request.form['task_id']
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('select a.id, task_id, employee_account_id, name, clock_in, clock_out, total_time, hourly_wage from '
                           'assigned a join employee_accounts e on a.employee_account_id = e.id where task_id = %s', (task_id,))
            assigned_list = []
            while True:
                row = cursor.fetchone()
                if row is None:
                    break
                assigned_list.append(row)
                print(row)
            print()
            print(assigned_list)
            if assigned_list:
                msg = 'Success!'
                session['valid_task'] = True
                session['task_input'] = task_id
            else:
                msg = 'Fail!'
                session['valid_task'] = False
            # Show the profile page with account info
            return render_template('tasks.html', account=account, list=assigned_list, msg=msg,
                                   session=session)
        else:
            msg = 'Please enter a valid task id: '
            return render_template('tasks.html', account=account, msg=msg)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/projects', methods=['GET', 'POST'])
def projects():
    # Check if user is loggedin
    session['valid_project'] = False
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employee_accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        if request.method == 'POST' and 'project_id' in request.form:
            # Create variables for easy access
            project_id = request.form['project_id']
            # Check if assignment exists using MySQL
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM task where project_id = %s ', (project_id,))
            task_list = []
            while True:
                row = cursor.fetchone()
                if row is None:
                    break
                task_list.append(row)
#                print(row)
#            print()
            print(task_list)
            if task_list:
                msg = 'Success!'
                session['valid_project'] = True
                session['project_input'] = project_id
            else:
                msg = 'Fail!'
                session['valid_project'] = False
            # Show the profile page with account info
            return render_template('projects.html', account=account, list=task_list, msg=msg, session=session)
        else:
            msg = 'Please enter a valid project id: '
            return render_template('projects.html', account=account, msg=msg)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/insert')
def insert():
    # Check if user is loggedin
    if 'loggedin' in session:
        return render_template('insert.html')
    else:
        return redirect(url_for('login'))


@app.route('/insert_account', methods=['GET', 'POST'])
def insert_account():
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        name = request.form['name']
        dept_id = request.form['dept_id']
        username = request.form['username']
        password = request.form['password']
        is_manager = request.form['is_manager']
        hourly_wage = request.form['hourly_wage']
        total_session_time=0
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employee_accounts WHERE username = %s', (username,))
        account = cursor.fetchone()
        # If account exists show error and validation checks
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[0-1]', is_manager):
            msg = 'Invalid value for manager!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not re.match(r'[A-Za-z0-9]+', name):
            msg = 'Name must contain only characters and numbers!'
        elif not password:
            msg = 'Please fill out the form!'
        else:
            # Account doesnt exists and the form data is valid, now insert new account into accounts table
            cursor.execute('INSERT INTO employee_accounts VALUES (DEFAULT, %s, %s, %s, %s, %s, DEFAULT, DEFAULT, %s, DEFAULT, %s)',
                           (dept_id, name, username, password, is_manager, total_session_time, hourly_wage))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
            return render_template('insert_account.html', msg=msg)
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    return render_template('insert_account.html', msg=msg)


@app.route('/insertassigned', methods=['GET', 'POST'])
def insertassigned():
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'employee_account_id' in request.form and 'task_id' in request.form:
        # Create variables for easy access
        employee_account_id = request.form['employee_account_id']
        task_id = request.form['task_id']
        total_session_time = 0
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employee_accounts WHERE id = %s', (employee_account_id,))
        account = cursor.fetchone()
        if account:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM task WHERE id = %s', (task_id,))
            account = cursor.fetchone()
            if account:
                cursor.execute('INSERT INTO assigned VALUES (DEFAULT, %s, %s, DEFAULT, DEFAULT, %s)',
                               (task_id, employee_account_id, total_session_time))
                mysql.connection.commit()

                msg = 'You have successfully assigned a task!'
                return render_template('insertassigned.html', msg=msg)
            else:
                msg = 'No task with that ID exists'
                return render_template('insertassigned.html', msg=msg)
        else:
            msg = 'No employee with that ID exists'
            return render_template('insertassigned.html', msg=msg)
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    return render_template('insertassigned.html', msg=msg)


@app.route('/insertproject', methods=['GET', 'POST'])
def insertproject():
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'name' in request.form and 'description' in request.form:
        # Create variables for easy access
        name = request.form['name']
        description = request.form['description']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        budget = request.form['budget']
        department_id = request.form['department_id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if not re.match(r'[A-Za-z0-9]+', name):
            msg = 'Project name must contain only characters and numbers'
        elif not re.match(r'[0-9]+', budget):
            msg = 'Budget must contain only numbers'
        elif not description and start_date and end_date:
            msg = 'Please fill out the form!'
        else:
            cursor.execute("INSERT INTO project VALUES (DEFAULT, %s, %s, %s, (select timestampadd(hour,'5:00:00', %s)), "
                           "(select timestampadd(hour,'5:00:00', %s)), %s, DEFAULT, DEFAULT, DEFAULT, DEFAULT)",
                           (name, description, department_id, start_date, end_date, budget,))
            mysql.connection.commit()


            msg = 'You have successfully made a new project!'
            return render_template('insertproject.html', msg=msg)
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    return render_template('insertproject.html', msg=msg)


@app.route('/inserttask', methods=['GET', 'POST'])
def inserttask():
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'name' in request.form and 'description' in request.form:
        # Create variables for easy access
        project_id = request.form['project_id']
        name = request.form['name']
        description = request.form['description']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        budget = request.form['budget']
        # cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if not re.match(r'[A-Za-z0-9]+', name):
            msg = 'Project name must contain only characters and numbers'
        elif not re.match(r'[0-9]+', budget):
            msg = 'Budget must contain only numbers'
        elif not description and start_date and end_date:
            msg = 'Please fill out the form!'
        else:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM project WHERE id = %s', (project_id,))
            account = cursor.fetchone()
            if account:
                cursor.execute("INSERT INTO task VALUES (DEFAULT, %s, %s, %s, (select timestampadd(hour,'5:00:00', %s)),"
                               "(select timestampadd(hour,'5:00:00', %s)), %s, DEFAULT, DEFAULT, DEFAULT)",
                               (name, description, project_id, start_date, end_date, budget))
                mysql.connection.commit()

                msg = 'You have successfully assigned a task to the project!'
                return render_template('inserttask.html', msg=msg)
            else:
                msg = 'No project with that ID exists'
                return render_template('inserttask.html', msg=msg)
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    return render_template('inserttask.html', msg=msg)


@app.route('/update')
def update():
    # Check if user is loggedin
    if 'loggedin' in session:
        return render_template('update.html')
    else:
        return redirect(url_for('login'))


@app.route('/updateaccount', methods=['GET', 'POST'])
def updateaccount():
    msg = ''
    msg2 = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'account_id' in request.form:
        # Create variables for easy access
        account_id = request.form['account_id']
        dept_id = request.form['dept_id']
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        is_manager = request.form['is_manager']
        hourly_wage = request.form['hourly_wage']

        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employee_accounts WHERE id = %s', (account_id,))
        account = cursor.fetchone()
        if account:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            if not (is_manager == ""):
                if re.match(r'[0-1]', is_manager):
                    print("Manager")
                    cursor.execute('UPDATE employee_accounts SET is_manager=%s WHERE id=%s', (is_manager, account_id,))
                    mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            if not (username == ""):
                if re.match(r'[A-Za-z0-9]+', username):
                    print("Username")
                    cursor.execute('UPDATE employee_accounts SET username=%s WHERE id=%s', (username, account_id,))
                    mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            if not (name == ""):
                if re.match(r'[A-Za-z0-9]+', name):
                    print("Name")
                    cursor.execute('UPDATE employee_accounts SET name=%s WHERE id=%s', (name, account_id,))
                    mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            if not (dept_id == ""):
                if re.match(r'[0-9]', dept_id):
                    cursor.execute('DELETE FROM assigned WHERE employee_account_id = %s', (account_id,))
                    mysql.connection.commit()
                    msg2 = 'All assignments tied to this account have been deleted (Department change). '
                    print("Department Id")
                    cursor.execute('UPDATE employee_accounts SET dept_id=%s WHERE id=%s', (dept_id, account_id,))
                    mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            if not (password == ""):
                print("Password")
                cursor.execute('UPDATE employee_accounts SET password=%s WHERE id=%s', (password, account_id,))
                mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            if not (hourly_wage == ""):
                print("Wages")
                cursor.execute('UPDATE employee_accounts SET hourly_wage=%s WHERE id=%s', (hourly_wage, account_id,))
                mysql.connection.commit()

            msg = 'You have successfully updated an account!'

            return render_template('updateaccount.html', msg=msg, msg2=msg2)
        else:
            msg = 'No account with that ID exists'
            return render_template('updateaccount.html', msg=msg)
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    return render_template('updateaccount.html', msg=msg)


@app.route('/updateassigned', methods=['GET', 'POST'])
def updateassigned():
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'assign_id' in request.form and 'task_id' in request.form:
        # Create variables for easy access
        assign_id = request.form['assign_id']
        employee_account_id = request.form['employee_account_id']
        task_id = request.form['task_id']
        total_session_time = 0
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM assigned WHERE id = %s', (assign_id,))
        account = cursor.fetchone()
        if account:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT a.id, department_id FROM assigned a join task t on a.task_id = t.id '
                           'join project p on t.project_id = p.id where a.id = %s', (assign_id,))
            assignm = cursor.fetchone()
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM employee_accounts WHERE id = %s', (employee_account_id,))
            employee = cursor.fetchone()

            if employee['dept_id'] is not assignm['department_id']:
                msg = 'Employee Department Id does not match Assignment Department Id. Please Update Employee Account First'
                return render_template('updateassigned.html', msg=msg)

            if not (employee_account_id == ""):
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute('SELECT * FROM employee_accounts WHERE id = %s', (employee_account_id,))
                account = cursor.fetchone()
                if account:
                    cursor.execute(
                        'UPDATE assigned SET employee_account_id=%s WHERE id = %s',
                        (employee_account_id, assign_id))
                    mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            if not (task_id == ""):
                cursor.execute('SELECT * FROM task WHERE id = %s', (task_id,))
                account = cursor.fetchone()
                if account:
                    cursor.execute(
                        'UPDATE assigned SET task_id=%s WHERE id = %s',
                        (task_id, assign_id))

            msg = 'You have successfully updated a task!'
            return render_template('updateassigned.html', msg=msg)
        else:
            msg = 'No assignment with that ID exists'
            return render_template('updateassigned.html', msg=msg)
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    return render_template('updateassigned.html', msg=msg)


@app.route('/updatetask', methods=['GET', 'POST'])
def updatetask():
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'task_id':
        # Create variables for easy access
        task_id = request.form['task_id']
        project_id = request.form['project_id']
        name = request.form['name']
        description = request.form['description']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        budget = request.form['budget']
        actual_start = request.form['actual_start']
        actual_end = request.form['actual_end']
        # cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM task WHERE id = %s', (task_id,))
        account = cursor.fetchone()
        if account:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            if not (project_id == ""):
                cursor.execute('SELECT * FROM project WHERE id = %s', (project_id,))
                account = cursor.fetchone()
                if account:
                    cursor.execute(
                        'UPDATE task SET project_id=%s'
                        ' WHERE id = %s',
                        (project_id, task_id))
                    mysql.connection.commit()
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            if not (actual_start == ""):
                cursor.execute(
                    'UPDATE task SET actual_start_date=%s'
                    ' WHERE id = %s',
                    (actual_start, task_id))
                mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            if not (actual_end == ""):
                cursor.execute(
                    'UPDATE task SET actual_end_date=%s'
                    ' WHERE id = %s',
                    (actual_end, task_id))
                mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            if not (start_date == ""):
                cursor.execute(
                    'UPDATE task SET planned_start_date=%s'
                    ' WHERE id = %s',
                    (start_date, task_id))
                mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            if not (budget == ""):
                if re.match(r'[0-9]+', budget):
                    msg = 'Budget must contain only numbers'
                    cursor.execute(
                        'UPDATE task SET planned_budget=%s'
                        ' WHERE id = %s',
                        (budget, task_id))
                    mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            if not (end_date == ""):
                cursor.execute(
                    'UPDATE task SET planned_end_date=%s'
                    ' WHERE id = %s',
                    (end_date, task_id))
                mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            if not (end_date == ""):
                cursor.execute(
                    'UPDATE task SET planned_end_date=%s'
                    ' WHERE id = %s',
                    (end_date, task_id))
                mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            if not (description == ""):
                cursor.execute(
                    'UPDATE task SET description=%s'
                    ' WHERE id = %s',
                    (description, task_id))
                mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            if not (name == ""):
                if re.match(r'[A-Za-z0-9]+', name):
                    cursor.execute(
                        'UPDATE task SET task_name=%s'
                        ' WHERE id = %s',
                        (name, task_id))
                    mysql.connection.commit()

            msg = 'You have successfully updated a task to the project!'
            return render_template('updatetask.html', msg=msg)
        else:
            msg = 'No task with that ID exists'
            return render_template('updatetask.html', msg=msg)
    elif request.method == 'POST':
        msg = 'Please fill out the form!'
        return render_template('updatetask.html', msg=msg)
    return render_template('updatetask.html', msg=msg)


@app.route('/updateproject', methods=['GET', 'POST'])
def updateproject():
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'name' in request.form and 'description' in request.form:
        # Create variables for easy access
        project_id = request.form['project_id']
        name = request.form['name']
        description = request.form['description']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        budget = request.form['budget']
        # cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM project WHERE id = %s', (project_id,))
        account = cursor.fetchone()
        if account:
            actual_start = request.form['actual_start']
            actual_end = request.form['actual_end']
            actual_budget = request.form['actual_budget']
            if not (actual_start == ""):
                cursor.execute('UPDATE project SET actual_start_date=%s WHERE id = %s', (actual_start, project_id))
                mysql.connection.commit()
                cursor.execute("UPDATE project SET actual_start_date = addtime(actual_start_date,'5:00')"
                               "WHERE id = %s", (project_id,))
                mysql.connection.commit()


            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            if not (actual_end == ""):
                cursor.execute('UPDATE project SET actual_end_date=%s WHERE id = %s', (actual_end, project_id))
                mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            if not (actual_budget == ""):
                cursor.execute(
                    'UPDATE project SET actual_budget=%s'
                    ' WHERE id = %s',
                    (actual_budget, project_id))
                mysql.connection.commit()


            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            if not (budget == ""):
                cursor.execute(
                    'UPDATE project SET planned_budget=%s'
                    ' WHERE id = %s',
                    (budget, project_id))
                mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            if not (start_date == ""):
                cursor.execute(
                    'UPDATE project SET planned_start_date=%s'
                    ' WHERE id = %s',
                    (start_date, project_id))
                mysql.connection.commit()


            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            if not (end_date == ""):
                cursor.execute(
                    'UPDATE project SET planned_end_date=%s'
                    ' WHERE id = %s',
                    (end_date, project_id))
                mysql.connection.commit()


            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            if not (description == ""):
                cursor.execute(
                    'UPDATE project SET project_description=%s'
                    ' WHERE id = %s',
                    (description, project_id))
                mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            if not (name == ""):
                if re.match(r'[A-Za-z0-9]+', name):
                    cursor.execute(
                        'UPDATE project SET project_name=%s'
                        ' WHERE id = %s',
                        (name, project_id))
                    mysql.connection.commit()

            msg = 'You have successfully updated the project!'
            return render_template('updateproject.html', msg=msg)

        else:
            msg = 'No project with that ID exists'
            return render_template('updateproject.html', msg=msg)

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    return render_template('updateproject.html', msg=msg)


@app.route('/delete')
def delete():
    # Check if user is loggedin
    if session['is_manager'] == 1 and 'loggedin' in session:
        return render_template('delete.html')
    else:
        return redirect(url_for('login'))


@app.route('/deleteassigned', methods=['GET', 'POST'])
def deleteassigned():
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'assign_id' in request.form:
        # Create variables for easy access
        assign_id = request.form['assign_id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM assigned WHERE id = %s', (assign_id,))
        account = cursor.fetchone()
        if account:
            deletestate = "DELETE FROM assigned WHERE id = %s"
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(deletestate, (assign_id,))
            mysql.connection.commit()

            msg = 'You have successfully deleted an assignment!'
            return render_template('deleteassigned.html', msg=msg)
        else:
            msg = 'No assignment with that ID exists'
            return render_template('deleteassigned.html', msg=msg)
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    return render_template('deleteassigned.html', msg=msg)


@app.route('/deleteaccount', methods=['GET', 'POST'])
def deleteaccount():
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'employee_account_id' in request.form:
        # Create variables for easy access
        employee_account_id = request.form['employee_account_id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employee_accounts WHERE id = %s', (employee_account_id,))
        account = cursor.fetchone()
        if account:
            deletestate2 = "DELETE FROM assigned WHERE employee_account_id = %s"
            deletestate = "DELETE FROM employee_accounts WHERE id = %s"
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM assigned WHERE employee_account_id = %s', (employee_account_id,))
            account = cursor.fetchone()
            if account:
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute(deletestate2, (employee_account_id,))
                mysql.connection.commit()
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(deletestate, (employee_account_id,))
            mysql.connection.commit()

            msg = 'You have successfully deleted an account!'
            return render_template('deleteaccount.html', msg=msg)
        else:
            msg = 'No account with that ID exists'
            return render_template('deleteaccount.html', msg=msg)
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    return render_template('deleteaccount.html', msg=msg)


@app.route('/deletetask', methods=['GET', 'POST'])
def deletetask():
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'task_id' in request.form:
        # Create variables for easy access
        task_id = request.form['task_id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM task WHERE id = %s', (task_id,))
        account = cursor.fetchone()
        if account:
            deletestate2 = "DELETE FROM assigned WHERE task_id = %s"
            deletestate = "DELETE FROM task WHERE id = %s"
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM assigned WHERE task_id = %s', (task_id,))
            account = cursor.fetchone()
            if account:
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute(deletestate2, (task_id,))
                mysql.connection.commit()
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(deletestate, (task_id,))
            mysql.connection.commit()

            msg = 'You have successfully deleted a task!'
            return render_template('deletetask.html', msg=msg)
        else:
            msg = 'No task with that ID exists'
            return render_template('deletetask.html', msg=msg)
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    return render_template('deletetask.html', msg=msg)


@app.route('/deleteproject', methods=['GET', 'POST'])
def deleteproject():
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'project_id' in request.form:
        # Create variables for easy access
        project_id = request.form['project_id']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM project WHERE id = %s', (project_id,))
        account = cursor.fetchone()
        if account:
            deletestate3 = "DELETE FROM assigned WHERE task_id IN (SELECT id FROM task WHERE project_id = %s)"
            deletestate2 = "DELETE FROM task WHERE project_id = %s"
            deletestate = "DELETE FROM project WHERE id = %s"

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('DELETE FROM warnings_on_projects WHERE project_id = %s', (project_id,))
            mysql.connection.commit()

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM assigned WHERE task_id IN (SELECT id FROM task WHERE project_id = %s)', (project_id,))
            account = cursor.fetchone()
            if account:
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute(deletestate3, (project_id,))
                mysql.connection.commit()
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM task WHERE project_id = %s', (project_id,))
            account = cursor.fetchone()
            if account:
                cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                cursor.execute(deletestate2, (project_id,))
                mysql.connection.commit()
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute(deletestate, (project_id,))
            mysql.connection.commit()
            msg = 'You have successfully deleted a project!'
            return render_template('deleteproject.html', msg=msg)
        else:
            msg = 'No project with that ID exists'
            return render_template('deleteproject.html', msg=msg)
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    return render_template('deleteproject.html', msg=msg)


@app.route('/changelog', methods=['GET', 'POST'])
def changelog():
    # Check if user is loggedin
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM employee_accounts WHERE id = %s', (session['id'],))
        assigned = cursor.fetchone()
        assignment2 = []
        cursor.execute('SELECT * FROM change_log ORDER BY id DESC')
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            assignment2.append(row)
            print(row)
        # User is loggedin show them the home page
        return render_template('changelog.html', account=assigned, list=assignment2)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run()
