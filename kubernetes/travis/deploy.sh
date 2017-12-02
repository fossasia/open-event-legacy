#!/usr/bin/env bash

export DEPLOY_BRANCH=${DEPLOY_BRANCH:-master}

if [ "$TRAVIS_PULL_REQUEST" != "false" -o "$TRAVIS_REPO_SLUG" != "fossasia/open-event-legacy" -o  "$TRAVIS_BRANCH" != "$DEPLOY_BRANCH" ]; then
    echo "Skip production deployment for a very good reason."
    exit 0
fi

export REPOSITORY="https://github.com/${TRAVIS_REPO_SLUG}.git"

sudo rm -f /usr/bin/git-credential-gcloud.sh
sudo rm -f /usr/bin/bq
sudo rm -f /usr/bin/gsutil
sudo rm -f /usr/bin/gcloud

curl https://sdk.cloud.google.com | bash;
source ~/.bashrc
gcloud components install kubectl

gcloud config set compute/zone us-west1-a
# Decrypt the credentials we added to the repo using the key we added with the Travis command line tool
openssl aes-256-cbc -K $encrypted_4bb89c4d55ba_key -iv $encrypted_4bb89c4d55ba_iv -in ./kubernetes/travis/eventyay-800baa8d3d1d.json.enc -out eventyay-800baa8d3d1d.json -d
mkdir -p lib
gcloud auth activate-service-account --key-file eventyay-800baa8d3d1d.json
export GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/eventyay-800baa8d3d1d.json
gcloud config set project eventyay
gcloud container clusters get-credentials vintage-cluster
cd kubernetes/images/web
docker build --build-arg COMMIT_HASH=$TRAVIS_COMMIT --build-arg BRANCH=$DEPLOY_BRANCH --build-arg REPOSITORY=$REPOSITORY --no-cache -t eventyay/legacy-server:$TRAVIS_COMMIT .
docker login -u="$DOCKER_USERNAME" -p="$DOCKER_PASSWORD"
docker tag eventyay/legacy-server:$TRAVIS_COMMIT eventyay/legacy-server:latest
docker push eventyay/legacy-server
kubectl set image deployment/web web=eventyay/legacy-server:$TRAVIS_COMMIT
kubectl set image deployment/web celery=eventyay/legacy-server:$TRAVIS_COMMIT
