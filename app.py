from flask import Flask, render_template, request, session, redirect, url_for, send_file
import os
import uuid
import hashlib
import pymysql.cursors
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = "super secret key"
IMAGES_DIR = os.path.join(os.getcwd(), "images")

connection = pymysql.connect(host="localhost",
                             user="root",
                             password="root",
                             db="finstagram",
                             charset="utf8mb4",
                             port=8889,
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return dec

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")

@app.route("/home")
@login_required
def home():
    return render_template("home.html", username=session["username"])

@app.route("/upload", methods=["GET"])
@login_required
def upload():
    return render_template("upload.html")

@app.route("/images", methods=["GET"])
@login_required
def images():
    with connection.cursor() as cursor:
        query1 = "SELECT * FROM Photo WHERE allFollowers = 1 OR photoID IN (SELECT photoID FROM Share NATURAL JOIN Belong NATURAL JOIN CloseFriendGroup WHERE Belong.username = %s) ORDER BY timestamp DESC"
        cursor.execute(query1, session["username"])
        img_data = cursor.fetchall()
        tag_data = []
        query2 = "SELECT fname, lname FROM Person WHERE username IN (SELECT username FROM Tag NATURAL JOIN Photo WHERE photoID = %s and acceptedTag = 1)"
        for image in img_data:
            cursor.execute(query2, (image["photoID"]))
            tag_data.append(cursor.fetchall())
        for i in range(len(img_data)):
            img_data[i]["tags"] = tag_data[i]
        return render_template("images.html", images=img_data)

@app.route("/proposeTag", methods=["GET", "POST"])
@login_required
def propose_tag():
    for data in request.form:
        photoID = data
    with connection.cursor() as cursor:
        query = "SELECT * FROM Photo WHERE photoID = %s"
        cursor.execute(query, (photoID))
        img_data = cursor.fetchall()
        query2 = "SELECT fname, lname FROM Person WHERE username IN (SELECT username FROM Tag NATURAL JOIN Photo WHERE photoID = %s and acceptedTag = 1)"
        cursor.execute(query2, (img_data[0]["photoID"]))
        tag_data = cursor.fetchall()
        img_data[0]["tags"] = tag_data
    return render_template("proposeTag.html", image=img_data[0])

@app.route("/submitTag", methods=["GET","POST"])
@login_required
def submit_tag():
    for key, val in request.form.items():
        photoID = key
        targee = val
    if tagee == session["username"]:
        accept = 1
    else:
        accept = 0
    lookup = {"photoID": int(photoID)}
    try:
        with connection.cursor() as cursor:
            query = "SELECT photoID FROM Photo WHERE allFollowers = 1 OR photoID IN (SELECT photoID FROM Share NATURAL JOIN Belong NATURAL JOIN CloseFriendGroup WHERE Belong.username = %s)"
            cursor.execute(query, (tagee))
            photos = cursor.fetchall()
            if lookup in photos:
                query = "INSERT INTO Tag (username, photoID, acceptedTag) VALUES (%s, %s, %s)"
                cursor.execute(query, (tagee, photoID, accept))
                message = "Successfully tagged user!"
            else:
                message = "Photo is not visible to this user!"
    except pymysql.err.IntegrityError:
        message = "User already tagged or does not exist!"

    with connection.cursor() as cursor:
        query = "SELECT * FROM Photo WHERE photoID = %s"
        cursor.execute(query, (photoID))
        img_data = cursor.fetchall()
        query2 = "SELECT fname, lname FROM Person WHERE username IN (SELECT username FROM Tag NATURAL JOIN Photo WHERE photoID = %s and acceptedTag = 1)"
        cursor.execute(query2, (img_data[0]["photoID"]))
        tag_data = cursor.fetchall()
        img_data[0]["tags"] = tag_data

    return render_template("proposeTag.html", image=img_data[0], message=message)



@app.route("/image/<image_name>", methods=["GET"])
def image(image_name):
    image_location = os.path.join(IMAGES_DIR, image_name)
    if os.path.isfile(image_location):
        return send_file(image_location, mimetype="image/jpg")

@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")

@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")

@app.route("/loginAuth", methods=["POST"])
def loginAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()

        with connection.cursor() as cursor:
            query = "SELECT * FROM person WHERE username = %s AND password = %s"
            cursor.execute(query, (username, hashedPassword))
        data = cursor.fetchone()
        if data:
            session["username"] = username
            return redirect(url_for("home"))

        error = "Incorrect username or password."
        return render_template("login.html", error=error)

    error = "An unknown error has occurred. Please try again."
    return render_template("login.html", error=error)

@app.route("/registerAuth", methods=["POST"])
def registerAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()
        firstName = requestData["fname"]
        lastName = requestData["lname"]
        
        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO person (username, password, fname, lname) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (username, hashedPassword, firstName, lastName))
        except pymysql.err.IntegrityError:
            error = "%s is already taken." % (username)
            return render_template('register.html', error=error)    

        return redirect(url_for("login"))

    error = "An error has occurred. Please try again."
    return render_template("register.html", error=error)

@app.route("/logout", methods=["GET"])
def logout():
    session.pop("username")
    return redirect("/")

@app.route("/uploadImage", methods=["POST"])
@login_required
def upload_image():
    if request.files:
        image_file = request.files.get("imageToUpload", "")
        image_name = image_file.filename
        filepath = os.path.join(IMAGES_DIR, image_name)
        image_file.save(filepath)
        follow = request.form["shared"]
        with connection.cursor() as cursor:
        	owner = session['username']
        	if request.form["caption"] != "":
        		query = "INSERT INTO Photo (photoOwner, timestamp, filePath, caption, allFollowers) VALUES (%s, %s, %s, %s, %s)"
        		cursor.execute(query, (owner, time.strftime('%Y-%m-%d %H:%M:%S'), image_name, request.form["caption"], follow))
        	else:
        		query = "INSERT INTO Photo (photoOwner, timestamp, filePath, allFollowers) VALUES (%s, %s, %s, %s)"
        		cursor.execute(query, (owner, time.strftime('%Y-%m-%d %H:%M:%S'), image_name, follow))
        if follow == "1":
        	message = "Image has been successfully uploaded to all."
        	return render_template("upload.html", message=message)
        else:
        	with connection.cursor() as cursor:
        		query = "SELECT * FROM Belong WHERE username = %s"
        		cursor.execute(query, (session['username']))
        	friend_groups = cursor.fetchall()
        	session["image_name"] = image_name
        	session["friend_groups"] = friend_groups
        	return redirect("/selectFriendGroup")
    else:
    	message = "Failed to upload image."
    	return render_template("upload.html", message=message)

@app.route("/selectFriendGroup", methods=["GET", "POST"])
@login_required
def select_friend_group():
	image_name = session["image_name"]
	friend_groups = session.pop("friend_groups")
	return render_template("selectFriendGroup.html", image_path=image_name, groups=friend_groups)

@app.route("/uploadFriendGroup", methods=["POST"])
@login_required
def upload_friend_group():
    if request.form:
        image_name = session.pop("image_name")
        with connection.cursor() as cursor:
            query = "SELECT photoID FROM Photo WHERE PhotoOwner = %s AND filePath = %s"
            cursor.execute(query, (session["username"], image_name))
        photo = cursor.fetchall()
        photo = photo[-1]["photoID"]
        with connection.cursor() as cursor:
            query = "INSERT INTO Share(groupName, groupOwner, photoID) VALUES (%s, %s, %s)"
            for group in request.form:
                group = group.split(" ///////////////////// ")
                groupName = group[0]
                groupOwner = group[1]
                cursor.execute(query, (groupName, groupOwner, photo))
        message = "Image has been successfully uploaded to the selected friend group(s)."
        return render_template("upload.html", message=message)
    else:
        message = "Please select at least one friend group."
        return render_template("selectFriendGroup.html", error=message)

@app.route("/follows", methods=["GET"])
@login_required
def follows():
    return render_template("follows.html")

@app.route("/followRequest", methods=["GET"])
@login_required
def follow_request():
    with connection.cursor() as cursor:
        query = "SELECT followerUsername FROM Follow WHERE followeeUsername = %s AND acceptedfollow = 0"
        cursor.execute(query, (session["username"]))
    data = cursor.fetchall()
    return render_template("followRequest.html", myFollowers=data)

@app.route("/followUser", methods=["POST"])
@login_required
def follow_user():
    if request.form:
        follower = session["username"]
        followee = request.form["followee"]
        try:
            query = "INSERT INTO Follow (followerUsername, followeeUsername, acceptedfollow) VALUES (%s, %s, 0)"
            with connection.cursor() as cursor:
                cursor.execute(query, (follower, followee))
            message = "successfully requested to follow"
            return render_template('follows.html', message=message)
        except pymysql.err.IntegrityError:
            message = "Username does not exist, there is a pending follow request to this username, or you are already following this username."
            return render_template("follows.html", message=message)

@app.route("/followAccept", methods=["POST"])
@login_required
def follow_accept():
    if request.form:
        with connection.cursor() as cursor:
            for follower, action in request.form.items():
                if action == "Accept":
                    query = "UPDATE Follow SET acceptedfollow = 1 WHERE followerUsername = %s AND followeeUsername = %s"
                else:
                    query = "DELETE FROM Follow WHERE followerUsername = %s AND followeeUsername = %s"
                cursor.execute(query, (follower, session["username"]))
    return redirect("/followRequest")


@app.route("/tags", methods=["GET"])
@login_required
def tags():
    with connection.cursor() as cursor:
        query = "SELECT * FROM Photo WHERE photoID IN (SELECT photoID FROM Tag WHERE username = %s AND acceptedTag = 0) ORDER BY timestamp DESC"
        cursor.execute(query, (session["username"]))
        img_data = cursor.fetchall()
        tag_data = []
        query2 = "SELECT fname, lname FROM Person WHERE username IN (SELECT username FROM Tag NATURAL JOIN Photo WHERE photoID = %s and acceptedTag = 1)"
        for image in img_data:
            cursor.execute(query2, (image["photoID"]))
            tag_data.append(cursor.fetchall())
        for i in range(len(img_data)):
            img_data[i]["tags"] = tag_data[i]
    return render_template("tags.html", images=img_data)

@app.route("/tagRequest", methods=["POST"])
@login_required
def tag_request():
    if request.form:
        with connection.cursor() as cursor:
            for photoID, action in request.form.items():
                if action == "Accept":
                    query = "UPDATE Tag SET acceptedTag = 1 WHERE username = %s AND photoID = %s"
                else:
                    query = "DELETE FROM Tag WHERE username = %s AND photoID = %s"
                cursor.execute(query, (session["username"], photoID))
    return redirect("/tags")


@app.route("/closeFriendGroup", methods=["GET"])
@login_required
def close_friend_group():
    with connection.cursor() as cursor:
        query = "SELECT * FROM Belong WHERE username = %s"
        cursor.execute(query, (session["username"]))
        friend_group_data = cursor.fetchall()
    return render_template("closeFriendGroup.html", groups=friend_group_data)

@app.route("/inviteFriend", methods=["GET","POST"])
@login_required
def invite_friend():
    if request.form:
        data = request.form["group"]
        data = data.split(" ///////////////////// ")
        groupName = data[0]
        groupOwner = data[1]
        group_data = {"groupName": groupName, "groupOwner": groupOwner}
        return render_template("inviteFriend.html", group=group_data)
    else:
        return redirect("/closeFriendGroup")

@app.route("/updateFriendGroup", methods=["POST"])
@login_required
def update_friend_group():
    print(request.form)
    for key, val in request.form.items():
        print()
        print(key)
        print()
        data = key.split(" ///////////////////// ")
        groupName = data[0]
        groupOwner = data[1]
        invite_user = val
        group_data = {"groupName": groupName, "groupOwner": groupOwner}
    try:
        with connection.cursor() as cursor:
            query = "INSERT INTO Belong (groupName, groupOwner, username) VALUES (%s, %s, %s)"
            cursor.execute(query, (groupName, groupOwner, invite_user))
        message = "Successfully added user to the friend group"
    except:
        message = "User already added to the friend group, user does not exist, or some other error occured. Try again."
    return render_template("inviteFriend.html", group=group_data, message=message)



if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run()
