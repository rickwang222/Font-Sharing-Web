
from flask import Flask, render_template, request, g, redirect, url_for, jsonify, send_file, session
from werkzeug.utils import secure_filename
import db
import io
from functools import wraps
import json
from os import environ as env
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv, find_dotenv
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode
app = Flask(__name__)
oauth = OAuth(app)
app.secret_key = env["flask_session_secret"]
AUTHO0_CLIENT_ID = env['auth0_client_id']
AUTHO0_CLIENT_SECRET = env['auth0_client_secret']
AUTHO0_DOMAIN = env['auth0_domain']

def fetch_token(name, request):
    token = OAuth2Token.find(
        name=name,
        user=request.user
    )
    return token.to_token()

auth0 = oauth.register(
    'auth0',
    client_id=AUTHO0_CLIENT_ID,
    client_secret=AUTHO0_CLIENT_SECRET,
    api_base_url='https://'+AUTHO0_DOMAIN,
    access_token_url='https://'+AUTHO0_DOMAIN+'/oauth/token',
    authorize_url='https://'+AUTHO0_DOMAIN+'/authorize',
    client_kwargs={
        'scope': 'openid profile email',
    },
    server_metadata_url=f"https://{AUTHO0_DOMAIN}/.well-known"
                        f"/openid-configuration",
    fetch_token=fetch_token,
)

def requires_auth(f):
  @wraps(f)
  def decorated(*args, **kwargs):
    if 'profile' not in session:
      # Redirect to Login page here
      return redirect('/login')
    return f(*args, **kwargs)
  return decorated

# have the DB submodule set itself up before we get started. groovy.
@app.before_first_request
def initialize():
    db.setup()
    
@app.route('/')
def home():
    with db.get_db_cursor() as cur:
        font_ids = db.get_font_ids()
        font_names = db.get_font_names()
        font_info = [[font_ids[n], font_names[n]] for n in range(len(font_ids))]
        sample_text = request.args.get('sample_text')
        for id in font_ids:
            return render_template('home.html', font_info=font_info, sample_text = sample_text)
        return render_template('home.html', font_info=font_info, sample_text = sample_text)

@app.route('/search', methods = ['POST', 'GET'])
def search():
    if request.method == 'POST':
        font_ids = []
        font_names = []
        search = request.form["search"]
        with db.get_db_cursor() as cur:
            search = "%"+search+"%" 
            cur.execute("select * from fonts where fname ILIKE %s;", (search,))
            
            rowcount = 0
            for row in cur:
                if (rowcount < 10):
                    font_ids.append(row['font_id'])
                    font_names.append(row['fname'])
                rowcount += 1
            font_info = [[font_ids[n], font_names[n]] for n in range(len(font_ids))]
    
    return render_template('search.html', font_info=font_info)

@app.route('/profile/<int:user_id>')
def profile(user_id):
    # determine if logged in user is accessing own profile
    current_id = -1
    if 'profile' in session:
        current_user = json.dumps(session['profile'])
        current_user_data = json.loads(current_user)
        current_id = current_user_data['user_id']

    user_json = db.get_user_data(user_id)
    data = json.loads(user_json[0])
    auth_id = data['sub']
    is_logged_in_user = current_id == auth_id

    user_json = db.get_user_data(user_id)
    user_info = json.loads(user_json[0])
    font_info = db.get_user_font_info(user_id)
    user_bio = db.get_user_bio(user_id)
    
    return render_template('profile.html', has_auth=is_logged_in_user, user_id=user_id, userinfo=user_info, font_info=font_info, user_bio=user_bio)

@app.route('/font')
def font():
    return render_template('font.html')
@app.route('/upload')
@requires_auth
def upload():
    return render_template('upload.html')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ['ttf','otf','fnt']
  
@app.route('/getFontName')
def get_font_name(font_id):
    font_row = db.get_font(font_id)
    name = font_row['fname']
    return name
@app.route('/getUploaderName')
def get_uploader_name(font_id):
    font_row = db.get_font(font_id)
    data = font_row['auth_id']
    # should only be None for fonts uploaded before auth0 implemented
    if data == None:
        return 'N/A'
    json_form = json.loads(data)
    # some auth0 json forms have different key values
    if 'given_name' in json_form and 'family_name' in json_form:
        uploader = json_form['given_name'] + ' ' + json_form['family_name']
    elif 'name' in json_form:
        uploader = json_form['name']
    else:
        uploader = 'Unknown'
    return uploader

def get_uploader_id(font_id):
    return db.get_uploader_id(font_id)

def get_current_user_id():
    user_data = json.dumps(session['jwt_payload'])
    return db.get_user_id(user_data)

app.jinja_env.globals.update(get_font_name=get_font_name)
app.jinja_env.globals.update(get_uploader_name=get_uploader_name)
app.jinja_env.globals.update(get_current_user_id=get_current_user_id)
app.jinja_env.globals.update(get_uploader_id=get_uploader_id)

@app.route('/details/<int:font_id>')
def font_details(font_id):
    font_row = db.get_font(font_id)
    font_id = font_row['font_id']
    font_name = font_row['fname']
    font_description = font_row['description']
    font_downloads = font_row['downloads']
    font_uploader_name = get_uploader_name(font_id)
    return render_template('description.html', id=font_id, name=font_name, description=font_description, downloads=font_downloads, uploader_name=font_uploader_name)
    
@app.route('/upload/<int:font_id>')
def view_font(font_id):
    db.download_font(font_id)
    font_row = db.get_font(font_id)
    stream = io.BytesIO(font_row["data"])
    return send_file(stream, attachment_filename=font_row["fname"])

@app.route('/upload', methods=['POST'])
@requires_auth
def upload_font():
    # check if the post request has the file part
    if 'font' not in request.files:
        return redirect(url_for("upload", status="Font Upload Failed: No selected file"))
    file = request.files['font']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        return redirect(url_for("upload", status="Error 2: Font Upload Failed: No selected file"))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        data = file.read()
        desc = request.form['descriptionBox']
        user_data=json.dumps(session['jwt_payload'])
        db.upload_font(data, filename, desc, 0, user_data)
    return redirect(url_for("home", status="Font Uploaded Succesfully"))

#auth0
@app.route('/callback')
def callback_handling():
    # Handles response from token endpoint
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()
    # Store the user information in flask session.
    session['jwt_payload'] = userinfo
    db.add_user(json.dumps(session['jwt_payload']))
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    return redirect(url_for('home'))

@app.route('/login')
def login():
    app.logger.info('logging in')
    return auth0.authorize_redirect(redirect_uri=url_for('callback_handling', _external = True))
    
@app.route('/logout')
def logout():
    # Clear session stored data
    session.clear()
    # Redirect user to logout endpoint
    params = {'returnTo': url_for('home', _external=True), 'client_id': AUTHO0_CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))

@app.route('/editDesc/<int:font_id>', methods=['POST'])
@requires_auth
def edit_font_desc(font_id):
    #authentification data
    user_json = db.get_font_user_data(font_id)
    data = json.loads(user_json[0])
    font_auth_id = data['sub']
    current_user = json.dumps(session['profile'])
    current_user_data = json.loads(current_user)
    current_id = current_user_data['user_id']
   
    new_desc = request.form.get("desc")
    app.logger.info(new_desc)
    # update description
    if current_id == font_auth_id:
        db.edit_font_desc(font_id, new_desc)
        return redirect(url_for("font_details", font_id=font_id))
    else:
        print("You do not have access to this")
        return redirect(url_for("font_details", font_id=font_id, status="AuthentificationError"))

@app.route('/delete/<int:font_id>', methods=['GET'])
@requires_auth
def delete_font(font_id):
    user_json = db.get_font_user_data(font_id)
    print("USER JSON: ", user_json)
    data = json.loads(user_json[0])
    font_auth_id = data['sub']
    
    print("FONT AUTH ID: ", font_auth_id)
    print("session[profile]", session['profile'])
    current_user = json.dumps(session['profile'])
    current_user_data = json.loads(current_user)
    current_id = current_user_data['user_id']
    if current_id == font_auth_id:
        print('DELETING USER UPLOADED FONT')
        db.delete_font(font_id)
    else:
        print("You do not have access to this")
        return redirect(url_for("font_details", font_id=font_id, status="AuthentificationError"))
    
    return redirect(url_for("home"))

@app.route('/fonts/<int:font_id>', methods=['GET'])
def get_font_data(font_id):
    font_row = db.get_font(font_id)
    stream = io.BytesIO(font_row['data'])
    return send_file(stream, attachment_filename = font_row['fname'])

@app.route('/editBio/<int:user_id>', methods=['GET', 'POST'])
def edit_bio(user_id):
    new_bio = request.form.get("bio")
    db.edit_user_bio(user_id, new_bio)
    return redirect(url_for("profile", user_id=user_id))