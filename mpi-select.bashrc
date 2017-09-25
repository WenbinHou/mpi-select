
if [ -z "$MPISELECT_ROOT_DIR" ]; then

export MPISELECT_ROOT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"

export MPISELECT_TMP_DIR="/tmp/mpi-select/${RANDOM}-${RANDOM}"
mkdir -p "$MPISELECT_TMP_DIR"


function mpi-select()
{
    if [ -z "$1" ]; then
        echo "Select your favorate MPI environment."
        echo "Possible implementations are:"
        find "${MPISELECT_ROOT_DIR}/mpi" -maxdepth 1 -name "*.bashrc" | while read LINE
        do
            echo "  - $(basename "$LINE" .bashrc)"
        done
        echo ""
        return 1
    fi

    if [ ! -r "${MPISELECT_ROOT_DIR}/mpi/$1.bashrc" ]; then 
        echo "ERROR: '${MPISELECT_ROOT_DIR}/mpi/$1.bashrc' is not found"
        return 1
    fi

    local SUFFIX="-${RANDOM}-${RANDOM}-${RANDOM}"

    if [ ! -z "${MPISELECT_MPI_DIFF_DUMP}" ]; then
        python "${MPISELECT_ROOT_DIR}/core.py" dump "${MPISELECT_TMP_DIR}/curr${SUFFIX}.dump"
        python "${MPISELECT_ROOT_DIR}/core.py" revert "${MPISELECT_TMP_DIR}/curr${SUFFIX}.dump" "${MPISELECT_MPI_DIFF_DUMP}" "${MPISELECT_TMP_DIR}/mpi-revert${SUFFIX}.bashrc"
        source "${MPISELECT_TMP_DIR}/mpi-revert${SUFFIX}.bashrc"
        rm "${MPISELECT_TMP_DIR}/curr${SUFFIX}.dump"
        rm "${MPISELECT_TMP_DIR}/mpi-revert${SUFFIX}.bashrc"
    fi
    export MPISELECT_MPI_DIFF_DUMP="$MPISELECT_TMP_DIR/diff${SUFFIX}.dump"

    python "${MPISELECT_ROOT_DIR}/core.py" dump "${MPISELECT_TMP_DIR}/mpi-old${SUFFIX}.dump"
    source "${MPISELECT_ROOT_DIR}/mpi/$1.bashrc"
    python "${MPISELECT_ROOT_DIR}/core.py" dump "${MPISELECT_TMP_DIR}/mpi-new${SUFFIX}.dump"
    python "${MPISELECT_ROOT_DIR}/core.py" diff "${MPISELECT_TMP_DIR}/mpi-old${SUFFIX}.dump" "${MPISELECT_TMP_DIR}/mpi-new${SUFFIX}.dump" "${MPISELECT_MPI_DIFF_DUMP}"
    rm "${MPISELECT_TMP_DIR}/mpi-old${SUFFIX}.dump"
    rm "${MPISELECT_TMP_DIR}/mpi-new${SUFFIX}.dump"
}


function _complete_mpi_select()
{
    local curr=${COMP_WORDS[COMP_CWORD]}
    local results=""
    while read LINE
    do
        local name="$(basename "$LINE" .bashrc)"
        results="$results $name"
    done <<< "$(find "${MPISELECT_ROOT_DIR}/mpi" -maxdepth 1 -name "*.bashrc")"

    COMPREPLY=( $(compgen -W "$results" -- $curr) )
    unset results
}

complete -F _complete_mpi_select mpi-select


function add-install-root()
{
    if [ -z "$1" ]; then
        return
    fi
    export PATH="$1/bin:$PATH"
    export LD_LIBRARY_PATH="$1/lib:$LD_LIBRARY_PATH"
    export LIBRARY_PATH="$1/lib:$LIBRARY_PATH"
    export C_INCLUDE_PATH="$1/include:$C_INCLUDE_PATH"
    export CXX_INCLUDE_PATH="$1/include:$CXX_INCLUDE_PATH"
    export PKG_CONFIG_PATH="$1/lib/pkgconfig:$PKG_CONFIG_PATH"
    export MANPATH="$1/share/man:$MANPATH"
}

fi  # [ -z "$MPISELECT_ROOT_DIR" ]

