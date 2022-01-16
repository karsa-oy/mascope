<template>
  <section class="mzcalib-modal">
    <b-modal
      :active.sync="isMzCalibModalActive"
      has-modal-card
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
    >
      <div class="columns">
        <div class="modal-card" style="width: 500px; height: 700px">
          <header class="modal-card-head">
            <p class="modal-card-title">Mass calibration</p>
          </header>
          <section class="modal-card-body" style="text-align: center">
            <!-- Stats figure -->
            <div id="mz-calib-stats-chart"></div>
            <!-- End of stats figure -->
            <!-- Stats table -->
            <b-table
              :data="mzCalibStatsTableRows"
              :columns="mzCalibStatsTableCols"
            >
            </b-table>
            <!-- End of stats table -->
          </section>
          <footer class="modal-card-foot">
            <b-button @click="isMzCalibModalActive = false"> Cancel </b-button>
            <div style="text-align: right">
              <b-button
                :disabled="!samplesSelected.length"
                @click="calibrateSelectedSamples()"
              >
                Apply to selected samples
              </b-button>
            </div>
          </footer>
        </div>
      </div>
    </b-modal>
  </section>
</template>

<script>
export default {
  name: "",
  components: {},
  props: {},
  computed: {},
  data: function () {
    return {
      mzCalibStatsTableCols: [],
      mzCalibStatsTableRows: [],
    };
  },
  methods: {
    calibrateSelectedSamples() {
      this.be.exportOneWayBindingProp(
        "mzCalibrateSamples",
        {
          filenames: this.samplesSelected,
          fit: this.mzCalibration.fit,
        },
        null,
        this.roomSid
      );
      this.isMzCalibModalActive = false;
    },
    drawMzCalibStatsFigure() {
      let mz = this.mzCalibration.stats["mz"];
      let preCalibDmz = this.mzCalibration.stats["preDmz"];
      let postCalibDmz = this.mzCalibration.stats["postDmz"];

      let ddmz = new Float32Array(mz.length);
      for (var i = ddmz.length; i-- > 0; ) {
        ddmz[i] = Math.abs(preCalibDmz[i]) - Math.abs(postCalibDmz[i]);
      }
      let preTrace = { x: mz, y: preCalibDmz, type: "bar", name: "Pre" };
      let postTrace = { x: mz, y: postCalibDmz, type: "bar", name: "Post" };
      let dTrace = { x: mz, y: ddmz, type: "line", name: "Diff" };

      Plotly.react(
        "mz-calib-stats-chart",
        [preTrace, postTrace, dTrace],
        {},
        this.figureConfig
      );
    },
    fitMzCalibFunction() {
      let peakTofs = this.isotopeTableCheckedRows.map((row) => row["peak tof"]);
      let peakMzs = this.isotopeTableCheckedRows.map((row) => row["peak mz"]);
      let exactMzs = this.isotopeTableCheckedRows.map((row) => row["mz"]);
      let mzCalibData = {
        peakTofs: peakTofs,
        peakMzs: peakMzs,
        exactMzs: exactMzs,
      };
      this.be.exportOneWayBindingProp(
        "fitMzCalibFunction",
        { ...mzCalibData, room: this.roomSid, uid: Math.random() },
        null,
        this.roomSid
      );
    },
    mzCalibrateButtonClicked() {
      this.fitMzCalibFunction();
      this.isMzCalibModalActive = true;
    },
    updateMzCalibStatsTable() {
      this.mzCalibStatsTableCols = [
        { field: "mz", label: "m/z" },
        { field: "preDmz", label: "pre m/z error" },
        { field: "postDmz", label: "post m/z error" },
      ];
      this.mzCalibStatsTableRows = [];
      for (let i in this.mzCalibration.stats.mz) {
        let row = {};
        for (let j in this.mzCalibStatsTableCols) {
          let key = this.mzCalibStatsTableCols[j].field;
          let value = this.mzCalibration.stats[key][i];
          row[key] = Math.round((value + Number.EPSILON) * 1000) / 1000;
        }
        this.mzCalibStatsTableRows.push(row);
      }
      console.log("this.mzCalibStatsTableRows: ", this.mzCalibStatsTableRows);
    },
    mzCalibCompoundTableCheckedRows: function () {
      this.updateMzCalibPeaks();
    },
    mzCalibration: function () {
      this.updateMzCalibStatsTable();
      this.drawMzCalibStatsFigure();
    },
  },
};
</script>

