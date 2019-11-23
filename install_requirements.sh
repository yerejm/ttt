#!/bin/sh
set -o pipefail
set -o errexit
pyenv versions | grep -v 2.7 | grep -v system | cut -c 3- | awk '{print $1}' > .python-version
for pyver in $(cat .python-version); do
    major_ver=`echo ${pyver} | awk -F. '{print $1}'`
    export PYENV_VERSION=${pyver}
    echo "Installing pip packages for python ${major_ver} (${pyver})"
    case ${major_ver} in
        3)
            pip install -r requirements.txt && pip install -r dev-requirements.txt
            ;;
        *)
            echo "Unknown python ${major_ver}!"
            ;;
    esac
done

pyenv rehash
