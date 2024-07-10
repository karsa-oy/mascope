import mascope_runtime as runtime
logger = runtime.logger.service('standard-lib')

class ActiveSequence:
    def __init__(
        self, num_spectra: int, window_size: float, p_vlm: bool, ref_spec: int
    ):
        self.num_spectra = num_spectra
        self.window_size = window_size
        self.p_vlm = p_vlm
        self.ref_spec = ref_spec

        self._the_list = []

        self.mz_avg = 0.0
        self.mz_lb = -50

        self._spectra_present = [False for _ in range(num_spectra)]

    def is_valid(self, heap):
        if self.p_vlm:
            if len(self._the_list) != self.num_spectra:
                return False

        if self.empty():
            return False

        if not heap.empty():
            # Check if next one in heap is within window
            if heap.top()[2] <= self.mz_avg * (1.0 + self.window_size):
                return False

        if self._the_list[-1][2] > self.mz_avg * (1.0 + self.window_size):
            return False

        if self._the_list[0][2] < self.mz_avg * (1.0 - self.window_size):
            return False

        return self.mz_lb < self.mz_avg * (1.0 - self.window_size)

    def empty(self):
        return len(self._the_list) == 0

    def advance_lower_bound(self):
        if self.empty():
            raise Exception(
                "ActiveSequence::advanceLowerBound(): ActiveSequence must be non empty"
            )

        old_size = float(len(self._the_list))
        t = self._the_list[0]
        spec_ind = t[0]
        self.mz_lb = t[2]

        if spec_ind >= self.num_spectra:
            raise Exception(
                "ActiveSequence::advanceLowerBound(): get<0>(t] >= nbOfSpectra"
            )

        if self._spectra_present[spec_ind] == False:
            raise Exception(
                "ActiveSequence::advanceLowerBound(): that spectrum should be present"
            )

        # Remove lowest m/z
        self._the_list = self._the_list[1:]
        # This spectrum is not present anymore
        self._spectra_present[spec_ind] = False

        # Update average m/z
        new_size = float(len(self._the_list))
        if new_size == 0:
            self.mz_avg = 0
            logger.debug(self.mz_avg)
        else:
            if self.ref_spec is None:
                self.mz_avg = (old_size * self.mz_avg - self.mz_lb) / new_size
            logger.debug(self.mz_avg)

    def insert(self, heap, peak):
        if heap.empty():
            return False

        if self.empty():
            t = heap.pop_and_feed(peak)

            if t[0] >= self.num_spectra:
                raise Exception("ActiveSequence::insert(): get<0>(t] >= nbOfSpectra")

            if self._spectra_present[t[0]]:
                raise Exception(
                    "ActiveSequence::insert(): this spectra should be absent"
                )

            self._spectra_present[t[0]] = True
            self._the_list.append(t)

            self.mz_avg = t[2]
            return True

        else:
            t = heap.top()
            spectra_indx = t[0]
            mz = t[2]

            if spectra_indx >= self.num_spectra:
                raise Exception("ActiveSequence::insert(): get<0>(t] >= nbOfSpectra")

            if self._spectra_present[spectra_indx]:
                return False

            if self.ref_spec is None:
                # No reference spectrum specified, update mz_avg
                old_size = float(len(self._the_list))
                new_mz_avg = (old_size * self.mz_avg + mz) / (old_size + 1)
            else:
                # Reference spectrum specified, try to fix mz_avg to mz of reference
                if spectra_indx == self.ref_spec:
                    new_mz_avg = mz
                else:
                    new_mz_avg = self.mz_avg

            if mz <= new_mz_avg * (1 + self.window_size):
                if self._the_list[0][2] >= (new_mz_avg * (1 - self.window_size)):
                    self._spectra_present[spectra_indx] = True
                    self.mz_avg = new_mz_avg
                    self._the_list.append(heap.pop_and_feed(peak))
                    return True

            return False
