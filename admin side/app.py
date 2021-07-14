from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, IntegerField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import datetime
import time
from datetime import timedelta
from flask_mail import Mail,Message
from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler


app = Flask(__name__)

#app.config.from_pyfile('/home/prachiti/Desktop/proj/Library-Management-System/config.py')
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '755435'
app.config['MYSQL_DB'] = 'iit_library'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Initializing MySQL
mysql = MySQL(app)

app.secret_key = 'secret123'

app.config.update(
    DEBUG=True,
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USERNAME='cs207hostelproject@gmail.com',
    MAIL_PASSWORD='cs207dbms'
)
mail=Mail(app)


def send_avial_mail(reciver,book):
    msg=Message('Book Available',
                sender='cs207hostelproject@gmail.com',
                recipients=[reciver])
    msg.body="The book"+str(book)+ "you put for hold is now available you can issue it from library"
    mail.send(msg)
    return

@app.route('/update_all', methods=['GET','POST'])
def autorun():
    current_time = time.strftime(
        r"%Y-%m-%d %H:%M:%S", time.localtime())
    cur = mysql.connection.cursor()
    cur.execute("select req_id,user_id, req_date from hold_requests")
    data=cur.fetchall()
    #print(data)
    today = time.strftime(current_time)
    for p in data:
        date1=str(p['req_date'])
        return_data = time.strftime(date1)
        datetimeFormat = '%Y-%m-%d %H:%M:%S'
        diff = datetime.datetime.strptime(today, datetimeFormat) \
            - datetime.datetime.strptime(today, datetimeFormat)
        if p['user_id']=='faclty':
            if diff.days>=30:
                cur.execute("delete from hold_requests where req_id=%s and user_id=%s and req_date=%s",[p['req_id'],p['user_id'],p['req_date']])
        if p['user_id']=='student':
            if diff.days>=10:
                cur.execute("delete from hold_requests where req_id=%s and user_id=%s and req_date=%s",
                            [p['req_id'], p['user_id'], p['req_date']])
    mysql.connection.commit()
    cur.close()
#--------------------------------------------------------------------
    current_time = time.strftime(
        r"%Y-%m-%d %H:%M:%S", time.localtime())
    cur = mysql.connection.cursor()
    cur.execute("select user_id, issue_data from book_issue_log")
    data = cur.fetchall()
    #print(data)
    today = time.strftime(current_time)
    for p in data:
        date1 = str(p['issue_data'])
        return_data = time.strftime(date1)
        datetimeFormat = '%Y-%m-%d %H:%M:%S'
        diff = datetime.datetime.strptime(today, datetimeFormat) \
               - datetime.datetime.strptime(today, datetimeFormat)
        if diff.days >= 15:
            cur.execute("update user set unpaid_fines=unpaid_fines+2 where user_id=%s",[p['user_id']])
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('index'))




@app.route('/')
def index():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')

class RegisterForm(Form):
    libId = StringField("Librarian Id", [validators.DataRequired()])
    username = StringField("Name", [validators.Length(min=1, max=100)])
    email = StringField(
        'User Email', [validators.Length(min=1, max=100)])
    address = TextAreaField("Address", [validators.Length(min=1, max=400)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
        ])
    confirm = PasswordField('Confirm Password')



# User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
        form = RegisterForm(request.form)
        if request.method == 'POST' and form.validate():
            lib_id = form.libId.data
            username = form.username.data
            email = form.email.data
            password = form.password.data
            address = form.address.data

            # Creating the cursor
            cur = mysql.connection.cursor()

            # Executing Query
            cur.execute("INSERT INTO librarian(lib_id, name, email, password, address) VALUES(%s, %s, %s, %s, %s)",
                        (lib_id ,username, email, password, address))

            # Commit to database
            mysql.connection.commit()

            # Close connection
            cur.close()

            flash("You are now registered.", 'success')

            return redirect(url_for('login'))

        return render_template('register.html', form=form)



# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        # Get form fields
        email = request.form.get('email')
        password_candidate = request.form.get('password')
        # Create Cursor
        cur = mysql.connection.cursor()

        # Get user by Username
        result = cur.execute(
            "SELECT * FROM librarian WHERE email = %s", (email,))

        if result > 0:

            # Get the stored hash
            data = cur.fetchone()
            password = data['password']

            # Comparing the Passwords
            if (password_candidate == password):

                # Password matched
                session['logged_in'] = True
                session['email'] = data['email']

                flash('You have successfully logged in', 'success')
                return redirect(url_for('bookslist'))

            else:
                error = 'Invalid login.'
                return render_template('login.html', error=error)

            # Close connection
            cur.close()

        else:
            error = 'Username not found.'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, please Login.', 'danger')
            return redirect(url_for('login'))
    return wrap

# Creating the Books list
@app.route('/bookslist', methods=['GET', 'POST'])
# @is_logged_in
def bookslist():

    # Create Cursor
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        searchbook = request.form['search']

        data = cur.execute("select * from book where title LIKE '" + str(searchbook)+"' and book_status = 'available' ")

        if data > 0:
            return redirect(url_for('issue_books', bookName=searchbook))
        else:
            msg = 'This book is not available right now'
            return render_template('bookslist.html', msg=msg)
    # Execute
    # where available <> 0
    result = cur.execute(
         "SELECT book_id, title, count(*) as available FROM book where book_status = 'available' GROUP BY isbn_no")

    books = cur.fetchall()
    if result > 0:
        return render_template('bookslist.html', books=books)
    else:
        msg = 'No books found'
        return render_template('bookslist.html', msg=msg)

    # Close connection
    cur.close()

# Issue books Form Class


class IssueForm(Form):
    bookName = StringField("Name of the book to be issued")
    user_id = StringField(
        "Student ID number", [validators.Length(min=1)])
    

# Add Report Form


@app.route('/issue_books/<string:bookName>', methods=['GET', 'POST'])
@is_logged_in
def issue_books(bookName):
    # Create Cursor
    cur = mysql.connection.cursor()
    result = cur.execute(
        "SELECT * FROM book WHERE title = %s", [bookName])

    book = cur.fetchone()

    # Get form
    form = IssueForm(request.form)

    # Populate form
    form.bookName.data = bookName
    if request.method == 'POST' and form.validate():
        print(book['copy_no'])
        if book['book_status']!='available':
            flash('BOOK cannot be Issued. Sorry book not available Student may put a hold request .')
            return render_template('issue_books.html', form=form)
        user_id = form.user_id.data
        title = form.bookName.data

        #checking for fine
        cur.execute("SELECT unpaid_fines FROM user WHERE user_id = %s",(user_id,))
        data = cur.fetchone()
        #checking if user already has issued 3 books
        max=cur.execute("SELECT count(%s) as books From book_issue_log where user_id =%s Group by issue_data ",[user_id,user_id])

        usn=cur.execute("SELECT count(%s) as books From hold_requests where book_id =%s Group by req_date ",[user_id,book['book_id']])

        bc=cur.execute("SELECT count(%s) as books From book_issue_log where user_id =%s and book_id=%s and return_data=%s Group by issue_data ",[user_id,user_id,book['book_id'],None])

        #check of hold
        cur.execute("SELECT user_id from hold_requests WHERE book_id=%s ORDER BY date(req_date) ASC",[book['book_id']])
        hd=cur.fetchmany(usn)
        if int(data['unpaid_fines']) >=1000:
        # Execute
            msg = 'BOOK cannot be Issued. Fine exceeding more than Rs.1000.'
            return redirect(url_for('pay_fine', msg = msg))
        elif max>=3:
            flash('BOOK cannot be Issued. Student already issued 3 books.')
            return render_template('issue_books.html', form=form)
        elif bc>=1:
            flash('BOOK cannot be Issued. Student has already issued this book.')
            return render_template('issue_books.html', form=form)
        elif len(hd)>0 and user_id not in hd:
            flash('BOOK cannot be Issued. Other student have put hold request before this student.')
            return render_template('issue_books.html', form=form)
        else:
            today=date.today()
            #issue_date = time.strftime(
              #  r"%Y-%m-%d ", today)
            cur.execute("INSERT INTO book_issue_log(user_id, book_id,issue_data) VALUES(%s, %s,%s)", (user_id, book['book_id'],today))
            cur.execute(
                    "UPDATE book SET book_status= 'on loan' WHERE book_id = "+str(book['book_id'])+"")
            cur.execute("Insert into user_bookshelf values(%s,%s,%s)",[user_id,book['book_id'],today])
        # Commit to MySQL
            mysql.connection.commit()

        # Close connection
            cur.close()

            flash('Book Issued', 'success')

            return redirect(url_for('bookslist'))

    return render_template('issue_books.html', form=form)


# Return books
class ReturnForm(Form):
    book_name = StringField("Name of the book to be returned")
    studentUsername = StringField(
        "Student ID number", [validators.Length(min=1)])


@app.route('/return_books', methods=['GET', 'POST'])
@is_logged_in
def return_books():
    cur_start = mysql.connection.cursor()
    result = cur_start.execute(
        "select title from book  group by title")
    books = cur_start.fetchall()
    form = ReturnForm(request.form)
    if result > 0:
        if request.method == 'POST' and form.validate():
            user_id = form.studentUsername.data
            book_name = form.book_name.data

            cur = mysql.connection.cursor()
            cur.execute("select book_id from book where title=%s",[book_name])
            booki=cur.fetchall()
            booki1=[]
            for i in range(len(booki)):
                booki1.append(booki[i]['book_id'])
            booki1=tuple(booki1)
            print(booki1)
            result = cur.execute("select book_id from book_issue_log where user_id=%s and book_id in %s",[user_id,booki1])
            data = cur.fetchone()
            if result > 0:
                book_id = data['book_id']

                #checking on hold
                hold = cur.execute("SELECT count(user_id) as count FROM hold_requests WHERE book_id = "+str(book_id)+"")
                tot_hold = cur.fetchone()

                cur.execute("SELECT user_id from hold_requests WHERE book_id=%s ORDER BY date(req_date) ASC",[data['book_id']])
                hd=cur.fetchone()
                if hd!=None and len(hd)>0:
                    cur.execute("SELECT email from user WHERE user_id=%s",hd[0])
                    ema=cur.fetchone()
                    send_avial_mail(ema,book_name)

                cur.execute(
                    "update book set book_status = 'available' where book_id = "+str(book_id)+" ")
                return_data =date.today()
                cur.execute("update book_issue_log set return_data=%s where user_id=%s and book_id=%s",[return_data,user_id,data['book_id']])
                mysql.connection.commit()
                flash('Book Returned', 'success')
                return redirect(url_for('bookslist'))

            else:
                flash('Book already returned', 'success')
                return redirect(url_for('bookslist'))
            cur.close()

    else:
        flash('No books found', 'success')

    return render_template('return_books.html', form=form, books=books)

# Check fine form


class GetUsernameForm(Form):
    studentUsername = StringField(
        "Student ID number", [validators.Length(min=1)])
    amountpaid = IntegerField("Student ID number")


@app.route('/check_fine', methods=['GET', 'POST'])
@is_logged_in
def check_fine():
    cur = mysql.connection.cursor()

    # Execute
    result = cur.execute(
        "SELECT user_id, unpaid_fines  FROM user where unpaid_fines > 0 GROUP BY user_id, unpaid_fines")

    books = cur.fetchall()

    if result > 0:
        return render_template('check_fine.html', books=books)
    else:
        msg = 'No outstanding fines'
        return render_template('check_fine.html', msg=msg)

    # Close connection
    cur.close()

# Pay Fine


@app.route('/pay_fine', methods=['GET', 'POST'])
@is_logged_in
def pay_fine():
    form = GetUsernameForm(request.form)
    data = 0
    newfine = 0

    if request.method == 'POST' and form.validate():
        student_id = form.studentUsername.data
        cur = mysql.connection.cursor()
        cur.execute(
            "select unpaid_fines from user where user_id=" + str(student_id) + "  ")
        data = cur.fetchone()
        print(data)
        if request.form.get('cal'):
            return render_template('pay_fine.html', form=form, data=data)
        else:
            amountpaid = form.amountpaid.data
            if amountpaid > 0 and int(data['unpaid_fines']) > 0:
                originalfine = int(data['unpaid_fines'])
                newfine = originalfine-int(amountpaid)
                print(newfine)
                cur.execute("update book_issue_log set unpaid_fines="+str(newfine) +
                            " where user_id="+str(student_id)+" ")

                mysql.connection.commit()

                flash('Amount was paid', 'success')

    return render_template('pay_fine.html', form=form, data=data, newfine=newfine)


@app.route('/analyse', methods=['GET', 'POST'])
@is_logged_in
def analyse():
    cur = mysql.connection.cursor()
    cur.execute("select name ,count(*) as num from user group by user_id, unpaid_fines order by unpaid_fines desc, num desc limit 5")
    data = cur.fetchall()
    print (data)
    mysql.connection.commit()
    return render_template('analyse.html', data=data)

@app.route('/calc_fine', methods=['GET', 'POST'])
@is_logged_in
def c_fine():
    cur = mysql.connection.cursor()

    # Execute
    result = cur.execute(
        "SELECT user_id, unpaid_fines  FROM user where unpaid_fines > 0 GROUP BY user_id, unpaid_fines")

    books = cur.fetchall()

    if result > 0:
        return render_template('check_fine.html', books=books)
    else:
        msg = 'No outstanding fines'
        return render_template('check_fine.html', msg=msg)

    # Close connection
    cur.close()



# Add books Form Class
class AddBooksForm(Form):
    title = StringField("Name of the book to be added", [validators.Length(min=1, max=1000)])
    isbn = StringField("Enter ISBN of book", [validators.DataRequired()])
    year = IntegerField("Enter year of Publication")
    author = StringField("Name of the Author")
    quantity = IntegerField("Enter the quantity to be added", [validators.DataRequired()])
    shelf_id = IntegerField("Enter Id of shelf book to be placed in")



# Add Report Form


@app.route('/add_books', methods=['GET', 'POST'])
@is_logged_in
def add_books():
    
    # Get form
    form = AddBooksForm(request.form)

    if request.method == 'POST' and form.validate():
        title = form.title.data
        isbn = form.isbn.data
        author = form.author.data
        year = form.year.data
        quantity = form.quantity.data
        # Execute
        while quantity:
            cur = mysql.connection.cursor()

            # Execute
            cur.execute(
                "INSERT INTO book(title, isbn_no, year, copy_no, book_status, author_name) VALUES(%s, %s, %s, %s, %s, %s)",
                (title, isbn, year, 1, 'available', author))
            # Commit to MySQL
            mysql.connection.commit()

            # Close connection
            cur.close()
            quantity -= 1

        flash('Books Added', 'success')

        return redirect(url_for('bookslist'))

    return render_template('add_books.html', form= form)



# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You have logged out.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
