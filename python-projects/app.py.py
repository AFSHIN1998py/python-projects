from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/projects')
def projects():
    projects = [
        {'title': 'ربات تلگرام', 'desc': 'ربات گزارش قیمت ارزهای دیجیتال'},
        {'title': 'تحلیل داده', 'desc': 'پردازش داده‌های مالی'},
        {'title': 'وب سایت', 'desc': 'پورتفولیو شخصی'}
    ]
    return render_template('projects.html', projects=projects)

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)