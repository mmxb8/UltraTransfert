"""R2 research selector. Same UTCP1 grammar; no production negotiation.

Search spends at most 3% of raw transport time between candidate boundaries.
One codec call can exceed that soft budget. CPU estimates use a 1.5 safety
factor because small samples underestimate full-block reconstruction costs.
These constants are hypotheses, not measured receiver capabilities.
"""
import time

from research.predictive_compression import (PredictiveEncoder, _sample, predict,
                                            frame, header)
from ultra.compression import compress, decompress, shuffle, MAX_BLOCK, CodecError

RESEARCH_VERSION = 'R2.1'
RAW = ('raw', 1, 'none')


class BudgetEncoder(PredictiveEncoder):
    def _select(self, data):
        start = time.perf_counter()
        sample = _sample(data, 4096)
        scale = len(data) / max(1, len(sample))
        raw_time = len(data) / self.rate
        budget = raw_time * .03
        self.last_search = []
        best_recipe, best_cost = RAW, raw_time
        if len(data) < 1024:
            return RAW
        # Order is data-independent. Width one is useful for text; width four
        # for numeric data. Expensive predictors are explored last.
        candidates = [(c,w,'none') for c in self.allowed if c != 'raw' for w in (1,4,8,2)]
        candidates += [(c,w,p) for c in self.allowed if c != 'raw'
                       for w in (4,8) for p in ('subtract','xor')]
        incompressible = 0
        for index, recipe in enumerate(candidates):
            if recipe[2] != 'none' and best_recipe[1] == 1:
                continue
            if time.perf_counter() - start >= budget:
                break
            codec, width, predictor = recipe
            t = time.perf_counter()
            encoded = compress(shuffle(predict(sample,width,predictor),width),codec)
            restored = predict(shuffle(decompress(encoded,codec,len(sample)),width,True),width,predictor,True)
            cost_cpu = time.perf_counter()-t
            if restored != sample:
                raise CodecError('Non-reversible sampled recipe')
            elapsed = time.perf_counter()-start
            cost = 1.5*cost_cpu*scale + len(encoded)*scale/self.rate + elapsed
            self.last_search.append({'recipe':recipe,'estimated_seconds':cost,
                                     'sample_encoded_bytes':len(encoded),
                                     'sample_codec_seconds':cost_cpu,
                                     'search_seconds':elapsed,'budget_seconds':budget})
            if index < 3 and len(encoded) >= len(sample)*.99:
                incompressible += 1
                if incompressible == 3:
                    break
            if cost < best_cost:
                best_recipe,best_cost = recipe,cost
        return best_recipe

    def encode(self, data):
        if len(data) > MAX_BLOCK:
            raise CodecError('Predictor block too large')
        retune = self.recipe is None or self.blocks % self.interval == 0
        if not retune and len(data) >= 4096 and self.recipe != RAW:
            # Re-evaluate the recipe's economics and ratio on changed content.
            sample = _sample(data)
            start = time.perf_counter()
            probe = frame(sample,self.recipe,fallback=False)
            from research.predictive_compression import unframe
            if unframe(probe) != sample:
                raise CodecError('Non-reversible reuse probe')
            estimated = (time.perf_counter()-start)*len(data)/len(sample)*1.5
            estimated += len(probe)*len(data)/len(sample)/self.rate
            if estimated >= len(data)/self.rate:
                self.recipe = RAW
        # Raw reuse is cheap, with periodic retuning. It deliberately may miss
        # a compressible content change for at most interval-1 blocks.
        if retune:
            self.recipe = self._select(data)
            self.searches += 1
        else:
            self.reused += 1
        encoded = frame(data,self.recipe)
        h,_ = header(encoded)
        self.recipe = h['codec'],h['width'],h['predictor']
        self.blocks += 1
        return encoded
