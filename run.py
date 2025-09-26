from flask import Flask, render_template, redirect, request, flash, url_for, send_from_directory

app = Flask(__name__)
app.secret_key = 'LI$cb3ds!gwgy2027'

@app.route('/')
def base():
    return redirect('lessons')

@app.route('/lessons')
def lessons():
    return render_template('lessons.html')

@app.route('/progress')
def score():
    return render_template('progress.html')

@app.route('/streak')
def streak():
    return render_template('streak.html')

@app.route('/timed')
def timed():
    return render_template('timed.html')

@app.route('/quests')
def quests():
    return render_template('quests.html')

@app.route('/vocabulary')
def vocabulary():
    return render_template('vocabulary.html')

@app.route('/vocabulary_practice')
def vocabulary_practice():
    return render_template('vocabulary_practice.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/ebrw_info')
def ebrw_info():
    return render_template('ebrw_info.html')

if __name__ == '__main__':
    app.run(debug=True)

