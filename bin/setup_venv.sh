# -*- sh -*-
# vi:ft=sh:

PYTHON_VERSION=3.8.2
USE_CONDA=true
NEW_VENV=false
if command -v module > /dev/null; then
    HAVE_MODULE=true
else
    HAVE_MODULE=false
fi

__OLDPWD="${OLDPWD:-${PWD}}"
__PWD="${PWD}"

cd "${POPEYE_HOME:?}" || false

# Check if the available python has the required version
if command -v python3 > /dev/null && [[ "$(python3 -V | awk '{print $2}')" == "${PYTHON_VERSION}" ]]; then
    USE_CONDA=false
elif [[ "${HAVE_MODULE}" == true ]]; then
    USE_CONDA=false
    module load swdev python/python/"${PYTHON_VERSION}"
else
    USE_CONDA=true
fi

arch="$(arch)"
if [[ "${USE_CONDA}" == true ]]; then
    conda deactivate >/dev/null 2>&1 || true

    if [[ ! -f ./.miniconda/bin/conda ]]; then
        rm -fr ./.miniconda
        tmpdir="$(mktemp -d)"
        trap 'rm -rf -- "${tmpdir}"' EXIT
        (
            cd "${tmpdir}" || false
            curl -L https://repo.anaconda.com/miniconda/Miniconda3-py38_4.9.2-Linux-"${arch}".sh -o ./miniconda.sh

            case $arch in
                x86_64)
                    hash='1314b90489f154602fd794accfc90446111514a5a72fe1f71ab83e07de9504a7'
                    ;;
                aarch64)
                    hash='b6fbba97d7cef35ebee8739536752cd8b8b414f88e237146b11ebf081c44618f'
                    ;;
                *)
                    echo 'Unsupported architecture' >&2
                    exit 1
                    ;;
            esac

            echo "SHA256 (miniconda.sh) = $hash" > ./miniconda.sh.sha256
            sha256sum --check ./miniconda.sh.sha256
        )
        sh "${tmpdir}"/miniconda.sh -b -p ./.miniconda
    fi

    . ./.miniconda/etc/profile.d/conda.sh

    if [[ ! -d ./venv-"${arch}" ]]; then
        conda create -y -p venv-"${arch}" python=${PYTHON_VERSION}
        NEW_VENV=true
    fi
    conda activate ./venv-"${arch}" >/dev/null 2>&1 || true
else
    deactivate >/dev/null 2>&1 || true

    if [[ ! -d ./venv-"${arch}" ]]; then
        python3 -m venv "venv-${arch}"
        NEW_VENV=true
    fi
    . ./venv-"${arch}"/bin/activate >/dev/null 2>&1 || true
fi

if [[ "${NEW_VENV}" == true ]]; then
    python3 -m pip install --no-cache-dir --upgrade pip wheel # Remove in favour --upgrade-deps in venv creation once py>=3.9 is used
    python3 -m pip install --no-cache-dir -r ./requirements/common.txt
fi

export PYTHONPATH=${POPEYE_HOME}/tools/lib_bin/install-${arch}:${POPEYE_HOME}/tools${PYTHONPATH:+:${PYTHONPATH}}
export PATH=${POPEYE_HOME}/bin:${PATH:?}

cd "${__OLDPWD}" || false
cd "${__PWD}" || false
unset __OLDPWD __PWD PYTHON_VERSION USE_CONDA NEW_VENV HAVE_MODULE
