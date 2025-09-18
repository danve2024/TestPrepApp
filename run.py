from flask import Flask, render_template, redirect, request, flash, url_for, send_from_directory

app = Flask(__name__)
app.secret_key = 'LI$cb3ds!gwgy2027'

@app.route('/')
def base():
    return redirect('lessons')

@app.route('/lessons')
def lessons():
    return render_template('lessons.html')

@app.route('/score')
def score():
    return render_template('score.html')

@app.route('/streak')
def streak():
    return render_template('streak.html')

@app.route('/timed')
def timed():
    return render_template('timed.html')

@app.route('/quests')
def quests():
    return render_template('quests.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

if __name__ == '__main__':
    app.run(debug=True)

