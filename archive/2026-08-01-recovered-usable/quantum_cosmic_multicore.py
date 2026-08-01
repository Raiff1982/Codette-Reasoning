"""
Quantum Cosmic Multicore experiment.

Recovered from QuantumCosmicMulticore.md, where the source was embedded in the
write-up rather than shipped as a .py file.  Fetches real exoplanet host-star
data and runs the perspective agents across a multiprocessing pool.
"""

import numpy as np
import os
import json
import random
import requests
from multiprocessing import Pool

CORES = 15

class CognitionCocooner:
    def __init__(self, storage_path="./astro_cocoons"):
        self.storage_path = storage_path
        if not os.path.exists(storage_path):
            os.makedirs(self.storage_path)
    def wrap(self,label,data):
        meta={"label":label,"data":data}
        fname=f"{label}_{random.randint(1000,9999)}_{os.getpid()}.cocoon"
        fpath=os.path.join(self.storage_path,fname)
        with open(fpath,"w") as f: json.dump(meta,f)

class PerspectiveAgent:
    def __init__(self,name): self.name=name
    def analyze(self,result,space_info=None):
        if self.name=="Quantum":
            return f"Quantum perspective: Measured value was {result}."
        elif self.name=="Newton":
            return f"Newtonian logic: State followed deterministic evolution from {space_info}."
        elif self.name=="Stardust":
            return f"Stardust agent: Interleaved {space_info} entropy!"
        else: return "Unknown perspective..."

def fetch_exoplanet_star_data():
    try:
        url = ('https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select+pl_hostname,pl_rade,pl_orbper+from+pscomppars+where+rownum+<2&format=json')
        res = requests.get(url,timeout=3)
        j=res.json()
        return j[0] if j else {"pl_hostname":"unknown"}
    except Exception:
        return {"pl_hostname":"unknown"}

def quantum_astro_experiment(space_entropy):
    radius=float(space_entropy.get("pl_rade") or 1.0)
    period=float(space_entropy.get("pl_orbper") or 1.0)
    superposition=np.array([random.random()*radius,random.random()*period])
    sigma=radius; rho=period; beta=8/3; x=0.1*radius; y=0.2*period; z=0.2*radius
    dt=0.01; steps=50
    for _ in range(steps):
        dx=sigma*(y-x)*dt; dy=(x*(rho-z)-y)*dt; dz=(x*y-beta*z)*dt
        x+=dx; y+=dy; z+=dz
    return superposition.tolist(), [x,y,z]

def codette_experiment_task(proc_id):
    cocoons=CognitionCocooner("./astro_cocoons")
    sp_data=fetch_exoplanet_star_data()
    qq_state, chaos_state = quantum_astro_experiment(sp_data)
    qa = PerspectiveAgent("Quantum")
    na = PerspectiveAgent("Newton")
    sa = PerspectiveAgent("Stardust")
    q_comment=qa.analyze(qq_state[0],sp_data)
    n_comment=na.analyze(chaos_state[0],sp_data)
    s_comment=sa.analyze("---",sp_data["pl_hostname"])
    record_dict={
       "stardust_input":sp_data,
       "quantum_state":qq_state,
       "chaos_state":chaos_state,
       "perspectives":[q_comment,n_comment,s_comment],
       "run_by_proc": proc_id,
       "pid": os.getpid()
    }
    cocoons.wrap(label="quantum_space_trial", data=record_dict)

if __name__=="__main__":
    pool = Pool(CORES)
    jobs = [i for i in range(CORES)]
    results = pool.map(codette_experiment_task, jobs)
