from flask import Flask, render_template, flash, redirect, url_for, session, logging, request,jsonify
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
import itertools
from datetime import datetime

app = Flask(__name__)
#/home/mugdha/Projects/Library_Management_System/config.py
#app.config.from_pyfile('D:\4th sem\lab\Assignment 3-dbms\Library-Management-System/config.py')

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'library'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# Initializing MySQL
mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

# Register Form Class
class RegisterForm(Form):
    studentName = StringField("Student Name", [validators.Length(min=1, max=100)])
    address=StringField("Address", [validators.Length(min=1,max=100)])
    user_id = StringField('Username', [validators.Length(min=1, max=25)])
    user_type=StringField("User_type(Entry can be either 'student' or 'faculty')", [validators.Length(min=1,max=100)])

    email = StringField('Email', [validators.Length(min=1, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
        ])
    confirm = PasswordField('Confirm Password')

#User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
        form = RegisterForm(request.form)
        if request.method == 'POST' and form.validate():
            studentName = form.studentName.data
            email = form.email.data
            address=form.address.data
            user_type=str(form.user_type.data)
            studentUsername = form.user_id.data
            password = sha256_crypt.encrypt(str(form.password.data))
            print(user_type)
            if user_type != 'student' and user_type!= 'faculty':
                flash("Entry can be either 'student' or 'faculty'",'danger')
                return redirect(url_for('register'))

            # Creating the cursor
            cur = mysql.connection.cursor()

            # Executing Query
            cur.execute("INSERT INTO user(user_id, email, name, user_type, address, password) VALUES(%s, %s, %s, %s, %s, %s)", (studentUsername, email, studentName, user_type, address, password))


            # Commit to database
            mysql.connection.commit()

            # Close connection
            cur.close()

            flash("You are now registered.", 'success')

            return redirect(url_for('login'))

        return render_template('register.html', form= form )

# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        #Get form fields
        studentUsername = request.form['studentUsername']
        password_candidate = request.form['password']

        # Create Cursor
        cur = mysql.connection.cursor()

        # Get user by Username
        result = cur.execute("SELECT * FROM user WHERE user_id = %s", [studentUsername])

        if result > 0:

            # Get the stored hash
            data = cur.fetchone()
            password = data['password']

            # Comparing the Passwords
            if sha256_crypt.verify(password_candidate, password):

                # Password matched
                session['logged_in'] = True
                session['user_id'] = studentUsername
                session['studentName']= data['name']
                # session['aadharNo'] = data['aadharNo']

                flash('You have successfully logged in', 'success')
                return redirect(url_for('bookslist'))

            else:
                error = 'Invalid login.'
                return render_template('login.html', error = error)

            #Close connection
            cur.close()

        else:
            error = 'Username not found.'
            return render_template('login.html', error = error)

    return render_template('login.html')


@app.route('/friends',methods=['POST','GET'])
def friends():
    
    cur2 = mysql.connection.cursor()
    result2=cur2.execute("select user.name,user.user_id from user where user_id in (select from_user_id from friend where to_user_id=%s and request_status='accepted' union select to_user_id from friend where from_user_id=%s and request_status='accepted')",[session["user_id"],session["user_id"],])
    if request.method=='POST':
        friendid=request.form.get('friendid')
        session['friend']=friendid
        return redirect(url_for('friendbookshelf'))
    if result2 > 0:
        data=cur2.fetchall()
        return render_template('friends.html',friends=data)
    else:
       return render_template('friends.html',friends='NULL')
        

@app.route("/livesearch",methods=["POST","GET"])
def livesearch():
    searchbox = request.form.get("text")
    cursor = mysql.connection.cursor()
    query = "select name from user where name LIKE '{}%' order by name".format(searchbox)#This is just example query , you should replace field names with yours
    cursor.execute(query)
    result = cursor.fetchall()
    return jsonify(result)      

    
@app.route("/searchfriend",methods=["POST","GET"])
def searchfriend():
   if(request.method=='POST'):
        if request.form.get('friendname'):
            username = request.form.get('friendname')
            session['friend_name']=username
            cur2 = mysql.connection.cursor()
            result2=cur2.execute("select user.name,user.user_id from user where user_id in (select from_user_id from friend where to_user_id=%s and request_status='accepted' union select to_user_id from friend where from_user_id=%s and request_status='accepted')",[session["user_id"],session["user_id"],])
            if result2>0:
                data=cur2.fetchall()
                for friend in data :
                    if username in friend["name"]:
                        friendid=friend["user_id"]
                        session['friend']=friendid
                        return redirect(url_for('friendbookshelf'))
                cur2.close()
        cur2 = mysql.connection.cursor()
        result=cur2.execute("select user_id from user where name = %s", (session['friend_name'],))
        friendid='NULL'
        if result>0:
            friendid=cur2.fetchall()
            friendid=friendid[0]['user_id']
            status='Send_request'
            result=cur2.execute("select request_status from friend where from_user_id=%s and to_user_id=%s",(session['user_id'],friendid))
            if result>0:
                status='Pending_request'
            result2=cur2.execute("select request_status from friend where to_user_id=%s and from_user_id=%s",(session['user_id'],friendid))
            if result2>0:
                status='Accept_request'
            if request.form.get('sendfriendrequest'):
                friendid=request.form.get('friendid')
                s=request.form.get('sendfriendrequest')
                if(s=='Send_request'):
                    cur2.execute('insert into friend(from_user_id,to_user_id,request_status) values (%s,%s,%s)',(session['user_id'],friendid,'Pending'))
                    mysql.connection.commit()
                    status='Pending_request'  
                if(s=='Accept_request'):
                    cur2.execute("update friend set request_status=%s where to_user_id=%s",('accepted',session['user_id']))
                    mysql.connection.commit()
                    session['friend']=friendid
                    return redirect(url_for('friendbookshelf'))
            return render_template('searchfriend.html', name=session['friend_name'],friendid=friendid,status=status)
        else:
            return render_template('searchfriend.html', name=session['friend_name'],friendid=friendid)
        
    
@app.route("/friendbookshelf",methods=["POST","GET"])
def friendbookshelf():
      cur = mysql.connection.cursor()
      result = cur.execute("SELECT c.title,c.isbn_no FROM user as s,user_bookshelf as b,book as c WHERE s.user_id = %s and b.user_id=%s and c.book_id=b.book_id", [session['friend'],session['friend']])
      if result>0:
          data=cur.fetchall()
          return render_template('bookshelf.html',books=data)
      else:
          data='NULL'
          return render_template('bookshelf.html', books=data)
                                                                                

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args,**kwargs)
        else:
            flash('Unauthorized, please Login.', 'danger')
            return redirect(url_for('login'))
    return wrap

# Creating the Books list
@app.route('/bookslist', methods=["POST","GET"] )

#@is_logged_in
def bookslist():
    cur = mysql.connection.cursor()
    if request.method=="POST":
     
     query = request.form.get("searchbox")
     query = '%' + query + '%'
     results = cur.execute("SELECT title,isbn_no,author_name, book_status from book WHERE title LIKE %s OR isbn_no LIKE %s OR author_name LIKE %s GROUP BY isbn_no", (query,query, query))
     
     #results = cur.execute("SELECT book.title,book.book_status,book.isbn_no,book_author.author_name FROM book,book_author WHERE book.title LIKE :%s OR book.isbn_no LIKE %s OR book_author.author_name LIKE %s and book_author.book_id=book.book_id", (query,query,query))
  #   results = cur.execute("SELECT book.title,book.book_status,book.isbn_no,book_author.author_name FROM book,book_author WHERE lower(book.title) LIKE :q OR book.isbn_no LIKE :q OR lower(book_author.author_name) LIKE :q and book_author.book_id=book.book_id", {"q": query})
     if results>0:
         search=cur.fetchall()
         return render_template('bookslist.html',books =  search)
     else:
        msg = 'No books found'
        return render_template('bookslist.html', msg= msg)
    
   
    result = cur.execute("Select title,isbn_no,author_name,count(if(book_status = 'available',1,NULL))'book_status'  from book  group by isbn_no")
    books = cur.fetchall()
    if result > 0:
        return render_template('bookslist.html', books = books)
    else:
        msg = 'No books found'
        return render_template('bookslist.html', msg= msg)
    # Close connection
    cur.close()
    
    
 



@app.route("/bookdetails/<id>",methods=["POST","GET"])
@is_logged_in
def bookdetails(id):
    cur = mysql.connection.cursor()
    result=cur.execute("select ratings.rating_id,ratings.book_id,ratings.user_id,ratings.rating_value,user.name from ratings,user where ratings.book_id in(select book_id from book where isbn_no= %s) and user.user_id=ratings.user_id and ratings.user_id=%s",(id,session['user_id']))
    ratings=cur.fetchall()
    result2=cur.execute("select reviews.review_id,reviews.book_id,reviews.user_id,reviews.review_text,user.name from reviews,user where reviews.book_id in(select book_id from book where isbn_no= %s) and user.user_id=reviews.user_id and reviews.user_id=%s",(id,session['user_id']))
    reviews=cur.fetchall()
    if request.method == "POST":
        if request.form.get('hold'):
            result2=cur.execute("select book_id from hold_requests where user_id=%s and book_id in(select book_id from book where isbn_no=%s)",(session['user_id'],id))
            if result2==0:
                now= datetime.now()
        # Execute
                result2=cur.execute("select book_id from book where book_status='available' AND isbn_no =%s",(id,))
                if result2 > 0:
                    availability=cur.fetchone()
                    bookid = availability['book_id']
                    fine = cur.execute("SELECT unpaid_fines FROM user WHERE user_id = %s", (session['user_id'], ))
                    fine = cur.fetchone()
                    if fine['unpaid_fines'] <= 1000:
                        max=cur.execute("SELECT count(%s) as books From book_issue_log where user_id =%s Group by issue_data ",[session['user_id'],session['user_id'],])
                        if max<3:
                            cur.execute("INSERT INTO hold_requests(user_id, book_id,req_date)VALUES(%s, %s,%s)", (session['user_id'], bookid, now,))
                            cur.execute("UPDATE book SET book_status = 'hold' WHERE book_id = %s",(bookid, ))
                            mysql.connection.commit()
                            flash("Successfully placed a hold request",'success')
                        else:
                            flash("3 books already issued",'danger')
                    else :
                        flash("can't put a hold because fine is above 1000",'danger')
                else:
                    flash("book is not available",'danger')
            else:
                flash("You already have a request for this book",'danger')
        if request.form.get('comment'):
            if(result >0 or result2>0):
                flash("You already gave your review!",'danger')
            else:
                comment = request.form.get("comment")
                my_rating = request.form.get("rating")
                result=cur.execute("select user_bookshelf.book_id from user_bookshelf where user_bookshelf.user_id=%s and book_id in (select book_id from book where isbn_no=%s)",(session['user_id'],id))
                if result >0 :
                    data=cur.fetchone()
                    book_id=data['book_id']
                    cur.execute("INSERT INTO reviews(user_id,book_id,review_text) values(%s,%s,%s)",(session['user_id'],book_id,str(comment)))
                    cur.execute("insert into ratings(user_id,book_id,rating_value) values(%s,%s,%s)",(session['user_id'],book_id,my_rating))
                    mysql.connection.commit()
   # result3=cur.execute("select book.title,book.year,book.shelf_id,book.book_status,book.isbn_no,book_author.author_name from book inner join book_author on book.book_id=book_author.book_id where book.isbn_no=%s",(id,))
    result3=cur.execute("select title, year, shelf_id, book_status, isbn_no, author_name from book where isbn_no = %s", (id, ))
    if result3>0:
        result3=cur.fetchone()
        result=cur.execute("select ratings.rating_id,ratings.book_id,ratings.user_id,ratings.rating_value,user.name from ratings,user where ratings.book_id in(select book_id from book where isbn_no= %s) and user.user_id=ratings.user_id",(id,))
        ratings=cur.fetchall()
        result2=cur.execute("select reviews.review_id,reviews.book_id,reviews.user_id,reviews.review_text,user.name from reviews,user where reviews.book_id in(select book_id from book where isbn_no= %s) and user.user_id=reviews.user_id",(id,))
        reviews=cur.fetchall()
        count=0
        for rating in ratings:
            count=count+1
        return render_template('bookdetails.html',details=result3,ratings=ratings,reviews=reviews,count=count)


# Personal Details
@app.route('/student_detail')
@is_logged_in
def student_detail():

    # Create Cursor
    cur = mysql.connection.cursor()

    # Execute
    result = cur.execute("SELECT * FROM user WHERE user_id = %s", (session['user_id'], )) 

    profile = cur.fetchone()
    if result > 0:
        
        return render_template('student_detail.html',profile = profile )
    
    # Close connection
    cur.close()

@app.route('/mybooks')
@is_logged_in
def mybooks():
    # Create Cursor
    
    
    cur = mysql.connection.cursor()
    result = cur.execute("Select book.book_id, book.title, book.isbn_no, hold_requests.req_date from hold_requests INNER JOIN book ON hold_requests.book_id = book.book_id where hold_requests.user_id= %s", (session['user_id'], ))
    holdrequest = cur.fetchall()
    result1 = cur.execute("Select book.title, book.isbn_no, book_issue_log.issue_data,  IF(DATEDIFF(CURRENT_TIMESTAMP(),issue_data) > 5,'Overdue','Pending') as status from book INNER JOIN book_issue_log ON book_issue_log.book_id = book.book_id where book_issue_log.return_data IS NULL AND  book_issue_log.user_id = %s ORDER BY status",(session['user_id'], ) )
    bookstatus = cur.fetchall()
    if result>0 or result1 >0:
        return render_template ('mybooks.html',holdrequest = holdrequest, bookstatus = bookstatus);
    else:
        msg = 'No books found'
        return render_template('bookslist.html', msg= msg)
    # Close connection
    cur.close()

@app.route("/suggestions", methods=["POST","GET"])
@is_logged_in
def suggestions():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT b.title,b.isbn_no FROM book as b  where b.book_id in (select bs.book_id from user_bookshelf as bs where bs.user_id in ((select f.from_user_id from friend as f where f.to_user_id=%s) union (select f.to_user_id from friend as f where f.from_user_id=%s)))",[session["user_id"],session["user_id"],])
    if result > 0:
        data = cur.fetchall()
        return render_template('suggestions.html', books=data)
    else:
        data = 'NULL'
        return render_template('suggestions.html', books=data)


# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You have logged out.', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True)
