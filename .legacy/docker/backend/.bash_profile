

function init {
    printf "\033]2;%s\033\\" "$1" && poetry run "$@";
};
function prep-visualization {
  sleep 10;
  rm -rf DataViz_*.db;
};
export -f init prep-visualization;