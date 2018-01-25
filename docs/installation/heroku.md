---
title: Heroku
---

One-click Heroku deployment is available:

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

### Steps for Manual Deployment

* We need to install heroku on our machine. Type the following in your linux terminal:
	* ```wget -O- https://toolbelt.heroku.com/install-ubuntu.sh | sh```
  This installs the Heroku Toolbelt on your machine to access heroku from the command line.
* Next we need to login to our heroku server (assuming that you have already created an account). Type the following in the terminal:
	* ```heroku login```
    * Enter your credentials and login.
* Once logged in we need to create a space on the heroku server for our application. This is done with the following command
	* ```heroku create```
* Once the app is created, now it's time to set the `DATABASE_URL` env var.
    * ```heroku config:set DATABASE_URL=postgresql://postgres:start@localhost/test```
* After setting env vars, create the heroku database.
    * ```heroku addons:create heroku-postgresql:hobby-dev```
    * ```heroku pg:promote <HEROKU_POSTGRESQL_COLOR_URL>```
* Open Event uses Redis. Run the following to create a redis instance.
    * ```heroku addons:create heroku-redis:hobby-dev```
* Run `heroku config` to check the environment variables. `REDIS_URL` and `DATABASE_URL` should be set by now.
If they are missing, some problem has occured in the previous steps.
* Add python build pack to the app
    * ```heroku buildpacks:set heroku/python```
* Add Node.js build pack to the app
    * ```heroku buildpacks:add --index 2 heroku/nodejs```
* Then we deploy the code to heroku.
	* ```git push heroku master``` or
    * ```git push heroku yourbranch:master``` if you are in a different branch than master
* Finally, time to create tables on the server. Also in case of model updates, run the following command -
    * ```heroku run migrate```