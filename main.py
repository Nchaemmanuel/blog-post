from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os

# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, loginForm, Commentform


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
ckeditor = CKEditor(app)
Bootstrap5(app)

# TODO: Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app=app)

# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///my_posts.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# LOGIN MAGAGER CONFIGURATION
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # CREATE A FORIEN KEY INSIDE THE CHILD DB
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey('users.id'))
    author_re = relationship('User', back_populates='blog')
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(250), nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    comments =relationship('Comment', back_populates='parent_post')


# TODO: Create a User table for all your registered users. 
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    blog = relationship('BlogPost', back_populates='author_re')
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(1000))
    comments = relationship('Comment', back_populates='comment_author')
    
    
    
class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Child relationship:"users.id" The users refers to the tablename of the User class.
    # "comments" refers to the comments property in the User class.
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    # Child Relationship to the BlogPosts
    post_id: Mapped[str] = mapped_column(Integer, db.ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")

with app.app_context():
    db.create_all()


gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

# CREATING A DECORATION FUNCTION WHICH PREVENT EDITING ONLY TO ADMIN
def admin_only(func):
    @wraps(func)
    def decor(*args, **kwargs):
        if current_user != 1:
            return abort(403)
        else:
            return func(*args, **kwargs)
    return decor
        
            
        

# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=['GET','POST'])
def register():
    error = None
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        query_if_user_exist = db.session.execute(db.select(User).where(User.email == email))
        user = query_if_user_exist.scalar()
        if user:
            flash(message=f'Email already exist please try and logIn with {email}', category='exist')
            return redirect(url_for('login'))
        else:
            password = generate_password_hash(form.password.data, method='pbkdf2:sha256:60', salt_length=8)
            add_user = User(name=name, email=email, password=password)
            db.session.add(add_user)
            db.session.commit()
            login_user(add_user, remember=True)
            return redirect(url_for('register'))
    return render_template('register.html', form=form, error=error, current_user=current_user)
    


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    form = loginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        query_user = db.session.execute(db.select(User).where(User.email == email))
        user = query_user.scalar()
        if not user:
            flash(message='Invalid user, please register', category='register')
            return redirect(url_for('register'))
        elif not check_password_hash(user.password, password):
            flash(message='Incorrect password please try again', category='wrong password')
            return redirect(url_for('login'))
        else:
             # flash(message='successfully logIn', category='success')
            login_user(user=user, remember=True)
            return redirect(url_for('get_all_posts')) 
    return render_template("login.html", form=form, error=error, current_user=current_user)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts, current_user=current_user)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    form = Commentform()
    if form.validate_on_submit():
         if not current_user.is_authenticated:
            flash(message='you need to lognI/register first before you can comment on a post')
            # return redirect(url_for('show_post'))
         else:
            post_comment = form.commnet.data
            id = post_id
            add_to_comment = Comment(text=post_comment, author_id=current_user.id, post_id=id)
            db.session.add(add_to_comment)
            db.session.commit()
    display_comment = db.session.execute(db.select(Comment).where(Comment.post_id == post_id)).scalars().all()
    requested_post = db.get_or_404(BlogPost, post_id)
    return render_template("post.html", post=requested_post, current_user=current_user, 
                           form=form, comment=display_comment, gravatar=gravatar)


# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@login_required
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user.name,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@login_required
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


    

if __name__ == "__main__":
    app.run(debug=True, port=5005)
