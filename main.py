import config
import application


app = application.create_app(config.Config, debug=True)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
