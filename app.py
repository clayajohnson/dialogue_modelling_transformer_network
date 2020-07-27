from flask import Flask, render_template

app = Flask()

@app.route('/', methods=['GET', 'POST','HEAD'])
async def index():
    return render_template('index.html')
