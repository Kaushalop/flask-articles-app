#!/usr/bin/env python
from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)
app.debug = True

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'admin'
app.config['MYSQL_DB'] = 'myflaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# init my sql
mysql = MySQL(app)

#Articles = Articles()

@app.route('/')
def index():
      return render_template('home.html')
      

@app.route('/about')
def about():
    return render_template('about.html')

#Articles list
@app.route('/articles')
def articles():

    # Create Cursor
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()

    if result > 0:
        return render_template('articles.html', articles = articles)
    else:
        msg = 'No Articles found'
        return render_template('articles.html', msg = msg)

    cur.close()

# Single article
@app.route('/article/<string:id>/')
def article(id):

    # Create Cursor
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM articles WHERE id=%s", (id))

    article = cur.fetchone()

    if result > 0:
        return render_template('article.html', article = article)
    else:
        msg = 'Article Not found!'
        return render_template('article.html', msg = msg)

    cur.close()

# Register Form Class
class RegisterForm(Form):
    name = StringField(u'Name', validators=[validators.Length(min =1, max=50), validators.input_required()])
    username = StringField(u'Username', validators=[validators.Length(min =4, max=25), validators.input_required()])
    email = StringField(u'Email', validators=[validators.Length(min =6, max=50), validators.input_required()])
    password  = PasswordField(u'Password', validators=[
        validators.input_required(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField(u'Confirm Password')

# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email= form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        #create cursor
        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

        #Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('You are now registered and can login!', 'success')

        return redirect(url_for('index'))
    return render_template('register.html', form = form)

#user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        #Get form fields values
        username = request.form['username']
        password_candidate = request.form['password']

        # Create a cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result  = cur.execute("SELECT * from users WHERE username=%s", [username])

        # if any user found
        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            # Compare the passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed so create session variables
                session['logged_in'] = True
                session['username'] = username
                flash('You are now logged in!', 'success')

                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid Login'
                return render_template('login.html', error=error)
            
            #Close connection
            cur.close()
        else:
            error = 'User Not Found'
            return render_template('login.html', error=error)

    return render_template('login.html')

#Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

#lOGOUT
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out!', 'success')
    return redirect(url_for('login'))

# Dashboard            
@app.route('/dashboard')
@is_logged_in
def dashboard():

    # Create Cursor
    cur = mysql.connection.cursor()

    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()

    if result > 0:
        return render_template('dashboard.html', articles = articles)
    else:
        msg = 'No Articles found'
        return render_template('dashboard.html', msg = msg)

    cur.close()

# Article Form Class
class ArticleForm(Form):
    title = StringField(u'Title', validators=[validators.Length(min =1, max=200), validators.input_required()])
    body = TextAreaField(u'Body', validators=[validators.Length(min =30), validators.input_required()])

@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)", (title, body, session['username']))

        # Commit
        mysql.connection.commit()

        # Close
        cur.close()

        flash('Article Created!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_article.html', form=form)


@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):

    # Create cursor
    cur = mysql.connection.cursor()

    # Get the article by the ID
    result = cur.execute("SELECT * from articles WHERE id=%s", (id))

    article = cur.fetchone()

    #Get the form
    form = ArticleForm(request.form)

    # Populate Article Form fields
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s", (title, body, id))

        # Commit
        mysql.connection.commit()

        # Close
        cur.close()

        flash('Article Updated!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)

# Delete article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    # Create Cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM articles WHERE id=%s", (id))


    # Commit
    mysql.connection.commit()

    # Close
    cur.close()

    flash('Article Deleted!', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.secret_key='secret123'
    app.run()