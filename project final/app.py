from optparse import Values
from flask import Flask, render_template,request,flash,redirect,url_for,session
from flask_sqlalchemy import SQLAlchemy
import sqlite3
from datetime import date, datetime
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key="123"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite3' 
app.config['SESSION_TYPE'] = "filesystem"
db = SQLAlchemy(app)

class Tracker(db.Model):
    __tablename__ = 'Tracker'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tname = db.Column(db.String)
    tdesc = db.Column(db.String)
    ttype = db.Column(db.String)
    multi_select = db.Column(db.String(200), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'))                  #//TODO - Adding datetime obj
    tdata = db.relationship('TrackerData', backref="tracker")

class Users(db.Model):
    __tablename__ = 'Users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String, unique=True, nullable=False)            #//TODO - Hashing Password
    password = db.Column(db.String, nullable=False)
    trackers = db.relationship('Tracker', backref="user")

class TrackerData(db.Model):
    __tablename__ = 'TrackerData'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tracker_id = db.Column(db.Integer, db.ForeignKey('Tracker.id'))
    date = db.Column(db.String, nullable=False)
    value = db.Column(db.Integer, nullable=True)
    rad_value = db.Column(db.String, nullable=True)
    notes = db.Column(db.String, nullable=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login',methods=["GET","POST"])
def login():
    if request.method=='GET':
        return render_template('login.html')
    if request.method=='POST':
        name=request.form['name']
        password=request.form['password']
        exist_user = Users.query.all()
        flag = False
        for user in exist_user:
            if user.username == name and user.password == password:
                flag = True

        if flag:
            session["name"]=name
            session["password"]=password
            return redirect(url_for('customer', username = name))
        else:
            flash("Username and Password Mismatch","danger")
    return redirect(url_for("index"))

@app.route('/customer/<username>',methods=["GET","POST"])
def customer(username):
    curr_user = session.get('name')
    curr_user_obj = db.session.query(Users).filter(Users.username == curr_user).first()
    curr_user_id = curr_user_obj.id
    curr_user_tdata = db.session.query(Tracker).filter(Tracker.user_id == curr_user_id).all()
    return render_template("customer.html", tdata = curr_user_tdata, username=username)

@app.route('/customer/<username>/log/<tname>', methods=['GET','POST'])
def log(username, tname):
    if request.method == 'GET':
        flag = False
        user_obj = db.session.query(Users).filter(Users.username==username).first()
        user_trackers = db.session.query(Tracker).filter(Tracker.user_id==user_obj.id).all()
        for tracker in user_trackers:
            if tracker.tname == tname:
                curr_tracker=tracker
        if curr_tracker.multi_select != None:
            flag = True

        vals = curr_tracker.multi_select
        split_strip_values = []
        if vals != None:
            split_values = vals.split(',')
            for val in split_values:
                split_strip_values.append(val.strip())

        return render_template('log.html', values=split_strip_values, flag=flag)
    
    if request.method == "POST":
        curr_user = session.get('name')
        user_obj = db.session.query(Users).filter(Users.username==curr_user).first()
        user_trackers = db.session.query(Tracker).filter(Tracker.user_id==user_obj.id).all()
        for tracker in user_trackers:
            if tracker.tname == tname:
                curr_tracker=tracker

        value = request.form['value']
        notes = request.form['notes']
        dstring = datetime.now().strftime("%I:%M%p %B %d, %Y")
        tdata = TrackerData(tracker_id=curr_tracker.id, date=dstring, value=value, notes=notes)
        db.session.add(tdata)
        db.session.commit()
        return redirect('/customer/{username}'.format(username=session.get('name')))

@app.route('/customer/<username>/<tname>')
def view_tracker(username, tname):
    curr_user = session.get('name')
    user_obj = db.session.query(Users).filter(Users.username==curr_user).first()
    user_trackers = db.session.query(Tracker).filter(Tracker.user_id==user_obj.id).all()
    for tracker in user_trackers:
        if tracker.tname == tname:
            curr_tracker = tracker
    curr_tracker_logs = db.session.query(TrackerData).filter(TrackerData.tracker_id==curr_tracker.id).all()
    log_values_raw = []
    log_value_time = []
    for logs in curr_tracker_logs:
        log_values_raw.append(logs.value)
        log_value_time.append(logs.date)
    plt.plot(log_value_time, log_values_raw, marker='o', markerfacecolor='blue', markersize=12)
    plt.savefig('static/plt.png')
    plt.close()
    return render_template('view_tracker.html', username=curr_user, tracker=curr_tracker_logs)

@app.route('/customer/<username>/<int:tid>/<int:lid>/delete')
def del_log(username, tid, lid):
    curr_log = db.session.query(TrackerData).filter(TrackerData.id == lid).first()
    curr_tracker = db.session.query(Tracker).filter(Tracker.id == tid).first()
    db.session.delete(curr_log)
    db.session.commit()
    return redirect('/customer/{username}/{tname}'.format(username=username, tname=curr_tracker.tname))

@app.route('/customer/<username>/<int:tid>/<int:lid>/edit', methods = ['GET', 'POST'])
def edit_log(username, tid, lid):
    if request.method == 'GET':
        flag = False
        curr_log = db.session.query(TrackerData).filter(TrackerData.id == lid).first()
        curr_tracker = db.session.query(Tracker).filter(Tracker.id==tid).first()

        if curr_tracker.multi_select != None:
            flag = True

        vals = curr_tracker.multi_select
        split_strip_values = []
        if vals != None:
            split_values = vals.split(',')
            for val in split_values:
                split_strip_values.append(val.strip())

        return render_template('edit_log.html', log=curr_log, values=split_strip_values, flag=flag)
    if request.method == 'POST':
        value = request.form['value']
        notes = request.form['notes']
        curr_log = db.session.query(TrackerData).filter(TrackerData.id == lid).first()
        curr_tracker = db.session.query(Tracker).filter(Tracker.id == tid).first()
        curr_log.value = value
        curr_log.notes = notes
        db.session.commit()
        return redirect('/customer/{username}/{tname}'.format(username=username, tname=curr_tracker.tname))

@app.route('/tracker', methods=["GET", "POST"])
def tracker():
    if request.method == "GET":
        return render_template('addtracker.html')

    if request.method == "POST":
        tracker_name = request.form['name']
        desc = request.form['desc']
        ttype = request.form.getlist('type')[0]
        curr_user = session.get('name')
        curr_user_obj = db.session.query(Users).filter(Users.username==curr_user).first()
        curr_user_id = curr_user_obj.id
        if ttype == '1':
            tracker = Tracker(tname=tracker_name, tdesc=desc, ttype="integer", user_id=curr_user_id)
            db.session.add(tracker)
            db.session.commit()

        if ttype == '2':
            multi_select_values = request.form['settings']
            tracker = Tracker(tname=tracker_name, tdesc=desc, ttype="multiselect", multi_select=multi_select_values, user_id=curr_user_id)
            db.session.add(tracker)
            db.session.commit()

        return redirect(url_for('customer', username=curr_user))

@app.route('/customer/<username>/<int:tid>/delete')
def del_tracker(username, tid):
    curr_tracker = db.session.query(Tracker).filter(Tracker.id == tid).first()
    db.session.delete(curr_tracker)
    db.session.commit()
    return redirect('/customer/{username}'.format(username=username))

@app.route('/customer/<username>/<int:tid>/edit', methods=['GET', 'POST'])
def edit_tracker(username, tid):
    if(request.method == 'GET'):
        curr_tracker = db.session.query(Tracker).filter(Tracker.id == tid).first()
        print(curr_tracker.multi_select)
        return render_template('edit_tracker.html', tracker=curr_tracker)

    if request.method == 'POST':
        curr_tracker = db.session.query(Tracker).filter(Tracker.id == tid).first()
        name = request.form['name']
        desc = request.form['desc']
        multi_select = request.form['settings']
        curr_tracker.tname = name
        curr_tracker.tdesc = desc
        curr_tracker.multi_select = multi_select
        db.session.commit()
        return redirect('/customer/{username}'.format(username=username))

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method == 'GET':
         return render_template('register.html')
        
    if request.method == 'POST':
        name = request.form['name']
        pwd = request.form['password']

        flag = False
        exist_user = Users.query.all()
        for user in exist_user:
            if name == user.username:
                flag = True
            
        if flag:
            return redirect('register.html')
        else:
            user = Users(username=name, password=pwd)
            db.session.add(user)
            db.session.commit()
        return redirect('login')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
if __name__ == '__main__':
    app.run(debug=True)
