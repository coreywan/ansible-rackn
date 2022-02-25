#! /bin/sh

TAG='0.0.1'
git push --delete origin $TAG
git tag -d $TAG
git tag -a $TAG -m "{$TAG}"
git push origin --tags