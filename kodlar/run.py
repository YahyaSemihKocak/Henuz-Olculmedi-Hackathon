import json
import os
import csv
import time
import dimod
from neal import SimulatedAnnealingSampler
from dwave.system import EmbeddingComposite, DWaveSampler, LeapHybridCQMSampler
import argparse
from dimod import Binary, ConstrainedQuadraticModel
from dimod.binary import quicksum
import pulp
from pathlib import Path

def load_data(filepath='./small_pump_selection.json'):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_qubo(pumps, demand, max_capacity, alpha=100.0, beta=100.0):
    qubo = {}
    num_pumps = len(pumps)
    num_slacks = 11

    # Pompa değişkenleri
    for u in range(num_pumps):
        p1 = pumps[u]
        id1, cap1, cost1 = p1["pump_id"], p1["capacity_m3h"], p1["cost_tl"]

        for v in range(u, num_pumps):
            p2 = pumps[v]
            id2, cap2 = p2["pump_id"], p2["capacity_m3h"]

            if u == v:
                qubo[(f"y_{id1}", f"y_{id1}")] = (cost1 
                                    - 2 * alpha * demand * cap1 
                                    - 2 * beta * max_capacity * cap1 
                                    + (alpha + beta) * (cap1 ** 2))
            else:
                qubo[(f"y_{id1}", f"y_{id2}")] = 2 * (alpha + beta) * cap1 * cap2

        # Pompa - Slack etkileşimleri
        for i in range(num_slacks):
            val = 2 ** i
            qubo[(f"y_{id1}", f"s_1_{i}")] = -2 * alpha * cap1 * val
            qubo[(f"y_{id1}", f"s_2_{i}")] = 2 * beta * cap1 * val

    # Slack değişkenleri
    for i in range(num_slacks):
        val_i = 2 ** i
        for j in range(i, num_slacks):
            s1_i, s1_j = f"s_1_{i}", f"s_1_{j}"
            s2_i, s2_j = f"s_2_{i}", f"s_2_{j}"

            if i == j:
                qubo[(s1_i, s1_i)] = alpha * (2 * demand * val_i + (2 ** (2 * i)))
                qubo[(s2_i, s2_i)] = beta * (-2 * max_capacity * val_i + (2 ** (2 * i)))
            else:
                interaction = 2 ** (i + j + 1)
                qubo[(s1_i, s1_j)] = alpha * interaction
                qubo[(s2_i, s2_j)] = beta * interaction

    offset = alpha * (demand ** 2) + beta * (max_capacity ** 2)

    return qubo, offset

def sample_bqm(bqm, local=False, token=None):
    if local:
        sampler = SimulatedAnnealingSampler()
        return sampler.sample(bqm, num_reads=1000).first
    else:
        sampler = EmbeddingComposite(DWaveSampler(token=token))
        return sampler.sample(bqm).first

def export_submission_files(pumps, sample, qubo_energy, qubo_matrix, runtime_sec, alpha, beta):
    target_dir = Path.cwd() / "problem_01"
    target_dir.mkdir(exist_ok=True)

    # 1. pump_selection.csv
    total_cost, total_flow = 0.0, 0.0
    pump_rows = []
    for p in pumps:
        pid = p["pump_id"]
        selected = int(sample.get(f"y_{pid}", sample.get(pid, 0)))
        if selected == 1:
            total_cost += p["cost_tl"]
            total_flow += p["capacity_m3h"]
        pump_rows.append({
            "pump_id": pid,
            "name": p.get("name", ""),
            "capacity_m3h": p["capacity_m3h"],
            "cost_tl": p["cost_tl"],
            "selected": selected
        })

    with open(os.path.join(target_dir, "pump_selection.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["pump_id", "name", "capacity_m3h", "cost_tl", "selected"])
        writer.writeheader()
        writer.writerows(pump_rows)

    # 2. slack_bits.csv
    slack_vars = sorted([k for k in sample.keys() if k.startswith("s_")], key=lambda k: int(k.split("_")[1]))
    slack_rows = [{"bit_index": idx, "value": int(sample[k])} for idx, k in enumerate(slack_vars)]

    with open(os.path.join(target_dir, "slack_bits.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["bit_index", "value"])
        writer.writeheader()
        writer.writerows(slack_rows)

    # 3. qubo_matrix.json
    all_variables = sorted(list({var for pair in qubo_matrix.keys() for var in pair}))
    q_entries = [{"u": u, "v": v, "bias": float(b)} for (u, v), b in qubo_matrix.items() if b != 0]

    qubo_data = {
        "n_variables": len(all_variables),
        "variables": all_variables,
        "offset": 0.0,
        "Q": q_entries
    }

    with open(os.path.join(target_dir, "qubo_matrix.json"), "w", encoding="utf-8") as f:
        json.dump(qubo_data, f, indent=4)

    # 4. solution_summary.json
    summary_data = {
        "problem_id": "problem_01",
        "instance_id": "QUBO_SMALL_12P",
        "objective_value": round(total_cost, 2),
        "runtime_sec": round(runtime_sec, 4),
        "penalty_weights": {"alpha": float(alpha), "beta": float(beta)},
        "qubo_energy": float(qubo_energy),
        "slack_bits": [row["value"] for row in slack_rows],
        "n_variables": len(all_variables),
        "notes": f"Simulated Annealing solution. Total capacity: {round(total_flow, 2)} m3/h"
    }

    with open(os.path.join(target_dir, "solution_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=4)

def run_problem_01(token):
    data = load_data()
    pumps = data["pumps"]
    demand = data["demand_m3h"]
    max_capacity = data["max_capacity_m3h"]

    alpha, beta = 100.0, 100.0

    qubo, offset = build_qubo(pumps, demand, max_capacity, alpha=alpha, beta=beta)
    bqm = dimod.BinaryQuadraticModel.from_qubo(qubo, offset)

    start_time = time.time()
    best_solution = sample_bqm(bqm, token=token, local=False)
    runtime = time.time() - start_time

    export_submission_files(
        pumps=pumps,
        sample=best_solution.sample,
        qubo_energy=best_solution.energy,
        qubo_matrix=qubo,
        runtime_sec=runtime,
        alpha=alpha,
        beta=beta
    )

    total_flow = 0
    total_cost = 0
    for p in pumps:
        id = p["pump_id"]
        total_flow += sum([val * p["capacity_m3h"] for key, val in best_solution.sample.items() if key == f"y_{id}"])
        total_cost += sum([val * p["cost_tl"] for key, val in best_solution.sample.items() if key == f"y_{id}"])

    print(f"problem_01 sonuçları:\nSüre: {runtime:.4f} sn, Toplam akış: {total_flow}, Toplam maliyet: {total_cost}, Enerji: {best_solution.energy:.4f}\nSeçilen borular:")
    print([f"{key}: {val}" for key, val in best_solution.sample.items() if key[0] == 'y'])
    print(f"problem_01 dosyaları oluşturuldu")

# Model parametreleri
T_PERIOD   = 24.0
PI_TAL     = 25000.0     # karsilanamayan talep cezasi (TL/m3)
PI_MIN     = 100.0       # depo minimum seviye ihlali (TL/m3)
PI_KRI     = 800.0       # depo kritik seviye ihlali (TL/m3)
PI_TUK     = 25.0        # depo tuketimi firsat maliyeti (TL/m3)
RHO        = 0.001       # akis duzenleme (regularizasyon) (TL/m3)
TAU        = 0.002       # depo giris-cikis islem maliyeti (TL/m3)
SIGMA_HED  = 1.0         # donem sonu depo hedef orani
PI_SLACK   = 1.0e9

EPS = 1e-6


def log(msg):
    print(msg, flush=True)


# 1. VERI OKUMA
class Data:
    def __init__(self, data_dir, problem):
        self.problem = problem
        #veri çekme
        j = lambda f: json.load(open(os.path.join(data_dir, f), "r", encoding="utf-8"))

        self.arcs    = j("network_arcs.json")["arcs"]
        self.nodes   = j("network_nodes.json")["nodes"]
        src          = j("sources.json")
        self.sources = src["sources"]
        self.packages= src["source_packages"]
        pmp          = j("pumps.json")
        self.pumps   = pmp["pumps"]
        self.groups  = pmp["pump_groups"]
        self.tanks   = j("tanks.json")["tanks"]
        self.zones   = j("zones.json")["zones"]
        demands      = j("demands.json")["demands"]
        self.demand  = {d["zone_id"]: d for d in demands}

        # Problem 04: ariza sonucu kullanilamayan arklar
        self.unavailable = set()
        if problem == "problem_04":
            av = j("arc_availability.json")
            self.unavailable = set(av.get("unavailable_arc_ids", []))
            for aid, v in av.get("availability", {}).items():
                if int(v) == 0:
                    self.unavailable.add(aid)

        # indeksler
        self.arc_by_id  = {a["arc_id"]: a for a in self.arcs}
        self.node_in    = {n["node_id"]: [] for n in self.nodes}
        self.node_out   = {n["node_id"]: [] for n in self.nodes}
        for a in self.arcs:
            if a["to_node"]   in self.node_in:  self.node_in[a["to_node"]].append(a["arc_id"])
            if a["from_node"] in self.node_out: self.node_out[a["from_node"]].append(a["arc_id"])

        self.src_at  = {s["node_id"]: s["source_id"] for s in self.sources}
        self.tank_at = {r["node_id"]: r["tank_id"]   for r in self.tanks}
        self.zone_at = {z["node_id"]: z["zone_id"]   for z in self.zones}

        self.source_by_id = {s["source_id"]: s for s in self.sources}
        self.pump_by_id   = {p["pump_id"]:   p for p in self.pumps}
        self.tank_by_id   = {r["tank_id"]:   r for r in self.tanks}

        # pompa -> uyesi oldugu gruplar
        self.groups_of_pump = {}
        for g in self.groups:
            for pid in g["member_pump_ids"]:
                self.groups_of_pump.setdefault(pid, []).append(g)
        self.pkgs_of_source = {}
        for g in self.packages:
            for sid in g["member_source_ids"]:
                self.pkgs_of_source.setdefault(sid, []).append(g)

        self.total_demand = sum(self.dz(z["zone_id"]) for z in self.zones)

        log("  dugum %d | ark %d (kullanilamaz %d) | kaynak %d | pompa %d | depo %d | bolge %d"
            % (len(self.nodes), len(self.arcs), len(self.unavailable),
               len(self.sources), len(self.pumps), len(self.tanks), len(self.zones)))

    def dz(self, zone_id):
        d = self.demand[zone_id]
        return float(d.get("total_demand_m3h", float(d.get("normal_demand_m3h", 0.0)) + float(d.get("critical_demand_m3h", 0.0))))

    def dz_normal(self, zone_id):
        return float(self.demand[zone_id].get("normal_demand_m3h", 0.0))

    def dz_critical(self, zone_id):
        return float(self.demand[zone_id].get("critical_demand_m3h", 0.0))

    def arc_cap(self, a):
        if a["arc_id"] in self.unavailable:
            return 0.0
        return float(a["capacity_m3h"])

# 2) MODEL KURULUMU
class WaterModel:
    def __init__(self, D):
        self.D = D
        t0 = time.time()
        prob = pulp.LpProblem("SuDagitim_P02", pulp.LpMinimize)
        self.prob = prob

        A, S, P, R, Z = D.arcs, D.sources, D.pumps, D.tanks, D.zones
        split_demand = (D.problem == "problem_03")
        #Klasik içiin değişken tanımlama
        self.x = {a["arc_id"]: pulp.LpVariable("x_%s" % a["arc_id"], 0, D.arc_cap(a)) for a in A}
        self.q = {s["source_id"]: pulp.LpVariable("q_%s" % s["source_id"], 0, float(s["capacity_m3h"])) for s in S}
        self.w = {s["source_id"]: pulp.LpVariable("w_%s" % s["source_id"], 0, 1) for s in S}
        self.y = {p["pump_id"]:   pulp.LpVariable("y_%s" % p["pump_id"],   0, 1) for p in P}
        self.tp = {r["tank_id"]: pulp.LpVariable("tp_%s" % r["tank_id"], 0) for r in R}
        self.tm = {r["tank_id"]: pulp.LpVariable("tm_%s" % r["tank_id"], 0) for r in R}
        self.V  = {r["tank_id"]: pulp.LpVariable("V_%s" % r["tank_id"], 0, float(r["capacity_m3"])) for r in R}
        self.emin = {r["tank_id"]: pulp.LpVariable("emin_%s" % r["tank_id"], 0) for r in R}
        self.ekri = {r["tank_id"]: pulp.LpVariable("ekri_%s" % r["tank_id"], 0) for r in R}
        self.etuk = {r["tank_id"]: pulp.LpVariable("etuk_%s" % r["tank_id"], 0) for r in R}

        if split_demand:
            self.uN = {z["zone_id"]: pulp.LpVariable("uN_%s" % z["zone_id"], 0, D.dz_normal(z["zone_id"])) for z in Z}
            self.uK = {z["zone_id"]: pulp.LpVariable("uK_%s" % z["zone_id"], 0, D.dz_critical(z["zone_id"])) for z in Z}
            self.u  = None
        else:
            self.u  = {z["zone_id"]: pulp.LpVariable("u_%s" % z["zone_id"], 0, D.dz(z["zone_id"])) for z in Z}
            self.uN = self.uK = None

        self.sl_s = {s["source_id"]: pulp.LpVariable("sls_%s" % s["source_id"], 0) for s in S}
        self.sl_p = {p["pump_id"]:   pulp.LpVariable("slp_%s" % p["pump_id"],   0) for p in P}

        #Kısıtlarımızı Ekliyoruz
        obj = []
        for s in S:
            sid = s["source_id"]
            obj.append(T_PERIOD * float(s["cost_tl_m3"]) * self.q[sid])
            obj.append(float(s["activation_cost_tl"]) * self.w[sid])
        for p in P:
            pid = p["pump_id"]
            obj.append(float(p["fixed_on_cost"]) * self.y[pid])
            ec = T_PERIOD * float(p["variable_energy_cost"])
            for aid in p["out_arc_ids"]:
                if aid in self.x:
                    obj.append(ec * self.x[aid])
        for a in A:
            obj.append(T_PERIOD * (float(a["unit_cost_tl_m3"]) + RHO) * self.x[a["arc_id"]])
        for r in R:
            rid = r["tank_id"]
            obj.append(T_PERIOD * TAU * (self.tp[rid] + self.tm[rid]))
            obj.append(PI_MIN * self.emin[rid])
            obj.append(PI_KRI * self.ekri[rid])
            obj.append(PI_TUK * self.etuk[rid])
        for z in Z:
            zid = z["zone_id"]
            if split_demand:
                obj.append(T_PERIOD * PI_TAL * self.uN[zid])
                obj.append(T_PERIOD * PI_TAL * 10.0 * self.uK[zid])
            else:
                obj.append(T_PERIOD * PI_TAL * self.u[zid])
        for s in S: obj.append(PI_SLACK * self.sl_s[s["source_id"]])
        for p in P: obj.append(PI_SLACK * self.sl_p[p["pump_id"]])
        prob += pulp.lpSum(obj)

        for s in S:
            sid, cap = s["source_id"], float(s["capacity_m3h"])
            mn = float(s["min_flow_if_active_m3h"])
            prob += self.q[sid] - cap * self.w[sid] <= 0, "K1_%s" % sid
            prob += self.q[sid] + self.sl_s[sid] - mn * self.w[sid] >= 0, "K2_%s" % sid

        for p in P:
            pid = p["pump_id"]
            outs = [self.x[aid] for aid in p["out_arc_ids"] if aid in self.x]
            e = pulp.lpSum(outs) if outs else pulp.LpAffineExpression()
            prob += e - float(p["capacity_m3h"]) * self.y[pid] <= 0, "K4_%s" % pid
            prob += e + self.sl_p[pid] - float(p["min_flow_if_on"]) * self.y[pid] >= 0, "K5_%s" % pid

        for n in D.nodes:
            nid = n["node_id"]
            terms = [self.x[aid] for aid in D.node_in[nid]]
            terms += [-self.x[aid] for aid in D.node_out[nid]]
            rhs = 0.0
            if nid in D.src_at:
                terms.append(self.q[D.src_at[nid]])
            if nid in D.tank_at:
                rid = D.tank_at[nid]
                terms.append(self.tm[rid]); terms.append(-self.tp[rid])
            if nid in D.zone_at:
                zid = D.zone_at[nid]
                if split_demand:
                    terms.append(self.uN[zid]); terms.append(self.uK[zid])
                    rhs = D.dz(zid)
                else:
                    terms.append(self.u[zid])
                    rhs = D.dz(zid)
            prob += pulp.lpSum(terms) == rhs, "K6_%s" % nid

        for r in R:
            rid = r["tank_id"]
            v0, vmax = float(r["initial_volume_m3"]), float(r["capacity_m3"])
            vmin, vkri = float(r["min_level_m3"]), float(r["critical_level_m3"])
            prob += self.V[rid] - T_PERIOD * (self.tp[rid] - self.tm[rid]) == v0, "K7_%s" % rid
            prob += T_PERIOD * self.tm[rid] <= v0,   "K9_%s"  % rid
            prob += T_PERIOD * self.tp[rid] <= vmax, "K10_%s" % rid
            prob += self.V[rid] + self.emin[rid] >= vmin, "K11_%s" % rid
            prob += self.V[rid] + self.ekri[rid] >= vkri, "K12_%s" % rid
            prob += self.V[rid] + self.etuk[rid] >= SIGMA_HED * v0, "K13_%s" % rid

        for g in D.groups:
            mem = [self.y[pid] for pid in g["member_pump_ids"] if pid in self.y]
            if mem:
                prob += pulp.lpSum(mem) <= int(g["max_active"]), "K14_%s" % g["group_id"]
        for g in D.packages:
            mem = [self.w[sid] for sid in g["member_source_ids"] if sid in self.w]
            if mem:
                prob += pulp.lpSum(mem) <= int(g["max_active"]), "K15_%s" % g["package_id"]

        log("  model kuruldu: %d degisken, %d kisit  (%.1f sn)"
            % (len(prob.variables()), len(prob.constraints), time.time() - t0))

    def relax(self):
        for v in self.w.values(): v.cat = pulp.LpContinuous; v.lowBound, v.upBound = 0, 1
        for v in self.y.values(): v.cat = pulp.LpContinuous; v.lowBound, v.upBound = 0, 1
    #free_w ve free_y ye göre w ve y yi binary veya sabit olarak atama işlemi
    def set_integer(self, free_w, free_y, w_val, y_val):
        fw, fy = set(free_w), set(free_y)
        for sid, v in self.w.items():
            if sid in fw:
                v.cat = pulp.LpInteger; v.lowBound, v.upBound = 0, 1
            else:
                v.cat = pulp.LpContinuous
                b = float(w_val[sid]); v.lowBound = v.upBound = b
        for pid, v in self.y.items():
            if pid in fy:
                v.cat = pulp.LpInteger; v.lowBound, v.upBound = 0, 1
            else:
                v.cat = pulp.LpContinuous
                b = float(y_val[pid]); v.lowBound = v.upBound = b
    #başlangıç w ve y değerleri ayarlama
    def warm_start(self, w_val, y_val):
        try:
            for sid, v in self.w.items(): v.setInitialValue(float(w_val[sid]))
            for pid, v in self.y.items(): v.setInitialValue(float(y_val[pid]))
            return True
        except Exception:
            return False
    #verilen w_val ve y_val sözlüğüne göre bazı w ve y değerlerini sabitleme
    def fix(self, w_val, y_val):
        for sid, v in self.w.items():
            v.cat = pulp.LpContinuous
            b = float(w_val[sid]); v.lowBound = v.upBound = b
        for pid, v in self.y.items():
            v.cat = pulp.LpContinuous
            b = float(y_val[pid]); v.lowBound = v.upBound = b

    def solve(self, time_limit, gap=None, warm=False, msg=0):
        kw = dict(msg=msg, timeLimit=int(max(5, time_limit)))
        if gap is not None:
            kw["gapRel"] = gap
        if warm:
            kw["warmStart"] = True
            kw["keepFiles"] = True
        try:
            solver = pulp.PULP_CBC_CMD(**kw)
        except TypeError:
            kw.pop("warmStart", None); kw.pop("gapRel", None)
            solver = pulp.PULP_CBC_CMD(**kw)
        t0 = time.time()
        status = self.prob.solve(solver)
        return pulp.LpStatus[status], time.time() - t0

    def read_solution(self):
        val = lambda v: (v.varValue if v.varValue is not None else 0.0)
        D = self.D
        sol = {
            "obj":   float(pulp.value(self.prob.objective) or 0.0),
            "x":     {k: val(v) for k, v in self.x.items()},
            "q":     {k: val(v) for k, v in self.q.items()},
            "w":     {k: val(v) for k, v in self.w.items()},
            "y":     {k: val(v) for k, v in self.y.items()},
            "tp":    {k: val(v) for k, v in self.tp.items()},
            "tm":    {k: val(v) for k, v in self.tm.items()},
            "V":     {k: val(v) for k, v in self.V.items()},
            "emin":  {k: val(v) for k, v in self.emin.items()},
            "ekri":  {k: val(v) for k, v in self.ekri.items()},
            "etuk":  {k: val(v) for k, v in self.etuk.items()},
            "sl_s":  {k: val(v) for k, v in self.sl_s.items()},
            "sl_p":  {k: val(v) for k, v in self.sl_p.items()},
        }
        if self.u is not None:
            sol["u"]  = {k: val(v) for k, v in self.u.items()}
        else:
            sol["uN"] = {k: val(v) for k, v in self.uN.items()}
            sol["uK"] = {k: val(v) for k, v in self.uK.items()}
            sol["u"]  = {k: sol["uN"][k] + sol["uK"][k] for k in sol["uN"]}

        duals = {}
        for name, c in self.prob.constraints.items():
            pi = getattr(c, "pi", None)
            if pi:
                duals[name] = float(pi)
        sol["duals"] = duals

        sol["slack_total"] = sum(sol["sl_s"].values()) + sum(sol["sl_p"].values())
        sol["unmet_total"] = sum(sol["u"].values())
        sol["true_obj"] = sol["obj"] - PI_SLACK * sol["slack_total"]
        sol["n_pumps_on"]   = sum(1 for v in sol["y"].values() if v > 0.5)
        sol["n_sources_on"] = sum(1 for v in sol["w"].values() if v > 0.5)
        sol["service_rate"] = (100.0 * (1.0 - sol["unmet_total"] / D.total_demand)
                               if D.total_demand > 0 else 100.0)
        return sol


def is_admissible(sol):
    return sol["slack_total"] <= 1e-4


# 3) LP GEVSETMESI -> KESIRLI CEKIRDEK

def fractional_core(sol, tol=1e-6):
    core_w = [k for k, v in sol["w"].items() if tol < v < 1 - tol]
    core_y = [k for k, v in sol["y"].items() if tol < v < 1 - tol]
    return core_w, core_y

#gruplardaki  max aktive sayısının üzerinde aktive üye olmamasını sağlama işlemi
def repair_groups(D, w, y, score):
    for g in D.groups:
        mem = [p for p in g["member_pump_ids"] if p in y and y[p] == 1]
        k = int(g["max_active"])
        if len(mem) > k:
            mem.sort(key=lambda p: score.get(p, 0.0))
            for p in mem[k:]:
                y[p] = 0
    for g in D.packages:
        mem = [s for s in g["member_source_ids"] if s in w and w[s] == 1]
        k = int(g["max_active"])
        if len(mem) > k:
            mem.sort(key=lambda s: score.get(s, 0.0))
            for s in mem[k:]:
                w[s] = 0
    return w, y



# 4) KUANTUM ADIMI
def marginal_costs(D, sol):
    du = sol["duals"]
    delta = {}
    for p in D.pumps:
        pid = p["pump_id"]
        pi4 = min(0.0, du.get("K4_%s" % pid, 0.0))
        pi5 = max(0.0, du.get("K5_%s" % pid, 0.0))
        delta[pid] = (float(p["fixed_on_cost"])
                      + pi4 * float(p["capacity_m3h"])
                      + pi5 * float(p["min_flow_if_on"]))
    for s in D.sources:
        sid = s["source_id"]
        pi1 = min(0.0, du.get("K1_%s" % sid, 0.0))
        pi2 = max(0.0, du.get("K2_%s" % sid, 0.0))
        delta[sid] = (float(s["activation_cost_tl"])
                      + pi1 * float(s["capacity_m3h"])
                      + pi2 * float(s["min_flow_if_active_m3h"]))
    return delta


def build_cqm(D, base_w, base_y, free_w, free_y, delta, sol, aux=True):
    cqm = ConstrainedQuadraticModel()
    fw = {s: Binary("w_%s" % s) for s in free_w}
    fy = {p: Binary("y_%s" % p) for p in free_y}

    obj = []
    for s in free_w: obj.append(delta.get(s, 0.0) * fw[s])
    for p in free_y: obj.append(delta.get(p, 0.0) * fy[p])
    cqm.set_objective(quicksum(obj) if obj else quicksum([]))

    for g in D.groups:
        mem_free  = [p for p in g["member_pump_ids"] if p in fy]
        if not mem_free: continue
        fixed_on = sum(1 for p in g["member_pump_ids"] if p not in fy and base_y.get(p, 0) == 1)
        cap = int(g["max_active"]) - fixed_on
        if cap < len(mem_free):
            cqm.add_constraint(quicksum([fy[p] for p in mem_free]) <= max(0, cap),
                               label="K14_%s" % g["group_id"])

    for g in D.packages:
        mem_free = [s for s in g["member_source_ids"] if s in fw]
        if not mem_free: continue
        fixed_on = sum(1 for s in g["member_source_ids"] if s not in fw and base_w.get(s, 0) == 1)
        cap = int(g["max_active"]) - fixed_on
        if cap < len(mem_free):
            cqm.add_constraint(quicksum([fw[s] for s in mem_free]) <= max(0, cap),
                               label="K15_%s" % g["package_id"])

    if not aux: return cqm

    fixed_cap = sum(float(D.source_by_id[s]["capacity_m3h"])
                    for s in base_w if s not in fw and base_w[s] == 1)
    need = D.total_demand - fixed_cap
    if free_w and need > 0:
        caps = sorted((float(D.source_by_id[s]["capacity_m3h"]) for s in free_w), reverse=True)
        room = len(free_w)
        for g in D.packages:
            mem_free = [s for s in g["member_source_ids"] if s in fw]
            if mem_free:
                fixed_on = sum(1 for s in g["member_source_ids"] if s not in fw and base_w.get(s, 0) == 1)
                room = min(room, max(0, int(g["max_active"]) - fixed_on) + (len(free_w) - len(mem_free)))
        reach = sum(caps[:max(0, room)])
        if reach >= need:
            cqm.add_constraint(
                quicksum([float(D.source_by_id[s]["capacity_m3h"]) * fw[s] for s in free_w]) >= need,
                label="K_kapsama")

    carrying = [p for p in free_y if sol["y"].get(p, 0.0) > 1e-6]
    if len(carrying) >= 4:
        cap_by_group = {}
        for p in carrying:
            gs = D.groups_of_pump.get(p, [])
            key = gs[0]["group_id"] if gs else None
            cap_by_group.setdefault(key, []).append(p)
        room = 0
        for gid, mem in cap_by_group.items():
            if gid is None:
                room += len(mem)
            else:
                g = next(x for x in D.groups if x["group_id"] == gid)
                room += min(len(mem), int(g["max_active"]))
        target = int(0.5 * len(carrying))
        if room >= target and target >= 1:
            cqm.add_constraint(quicksum([fy[p] for p in carrying]) >= target,
                               label="K_akis_kapsama")
    return cqm


def sample_cqm(cqm, token, time_limit):
    ss = LeapHybridCQMSampler(token=token).sample_cqm(
        cqm, time_limit=max(5, int(time_limit)), label="qlns_water")
    feas = ss.filter(lambda r: r.is_feasible)
    use = feas if len(feas) else ss
    out = []
    for rec in use.data(fields=["sample"], sorted_by="energy"):
        out.append(dict(rec.sample))
        if len(out) >= 8: break
    return out


def apply_sample(base_w, base_y, sample):
    w, y = dict(base_w), dict(base_y)
    for k, v in sample.items():
        if k.startswith("w_"):
            sid = k[2:]
            if sid in w: w[sid] = int(round(v))
        elif k.startswith("y_"):
            pid = k[2:]
            if pid in y: y[pid] = int(round(v))
    return w, y


def expand_free_set(D, sol, free_w, free_y, max_add=500):
    viol_p = [pid for pid, v in sol["sl_p"].items() if v > 1e-4]
    viol_s = [sid for sid, v in sol["sl_s"].items() if v > 1e-4]
    if not viol_p and not viol_s:
        return list(free_w), list(free_y), 0

    add_y, add_w = set(), set(viol_s)
    add_y.update(viol_p)

    for pid in viol_p:
        for g in D.groups_of_pump.get(pid, []):
            add_y.update(g["member_pump_ids"])
    for sid in viol_s:
        for g in D.pkgs_of_source.get(sid, []):
            add_w.update(g["member_source_ids"])

    seed_nodes = set()
    for pid in viol_p:
        p = D.pump_by_id.get(pid)
        if p: seed_nodes.add(p["node_id"])
    nb = set(seed_nodes)
    for n in seed_nodes:
        for aid in D.node_in.get(n, []):
            nb.add(D.arc_by_id[aid]["from_node"])
        for aid in D.node_out.get(n, []):
            nb.add(D.arc_by_id[aid]["to_node"])
    for pid, p in D.pump_by_id.items():
        if p["node_id"] in nb: add_y.add(pid)
    for s in D.sources:
        if s["node_id"] in nb: add_w.add(s["source_id"])

    new_y = list(free_y)
    new_w = list(free_w)
    added = 0
    for pid in add_y:
        if pid in D.pump_by_id and pid not in new_y and added < max_add:
            new_y.append(pid); added += 1
    for sid in add_w:
        if sid in D.source_by_id and sid not in new_w:
            new_w.append(sid); added += 1
    return new_w, new_y, added



# 5) GONDERI URETIMI(bizden istenilen dosyaları üretme)

def export(D, sol, outdir, summary):
    os.makedirs(outdir, exist_ok=True)
    W = lambda f: csv.writer(open(os.path.join(outdir, f), "w", newline="", encoding="utf-8"))

    w = W("source_dispatch.csv")
    w.writerow(["source_id", "production_m3h", "is_active"])
    for s in D.sources:
        sid = s["source_id"]
        w.writerow([sid, round(sol["q"][sid], 4), int(round(sol["w"][sid]))])

    w = W("pump_operation.csv")
    w.writerow(["pump_id", "is_on"])
    for p in D.pumps:
        pid = p["pump_id"]
        w.writerow([pid, int(round(sol["y"][pid]))])

    w = W("arc_flows.csv")
    w.writerow(["arc_id", "flow_m3h"])
    for a in D.arcs:
        f = sol["x"][a["arc_id"]]
        if f > 1e-6:
            w.writerow([a["arc_id"], round(f, 4)])

    w = W("tank_levels.csv")
    w.writerow(["tank_id", "fill_rate_m3h", "discharge_rate_m3h", "end_volume_m3",
                "min_level_shortfall_m3", "critical_level_shortfall_m3",
                "depletion_vs_initial_m3"])
    for r in D.tanks:
        rid = r["tank_id"]
        w.writerow([rid, round(sol["tp"][rid], 4), round(sol["tm"][rid], 4),
                    round(sol["V"][rid], 4), round(sol["emin"][rid], 4),
                    round(sol["ekri"][rid], 4), round(sol["etuk"][rid], 4)])

    w = W("demand_service.csv")
    if D.problem == "problem_03":
        w.writerow(["zone_id", "unmet_normal_m3h", "unmet_critical_m3h"])
        for z in D.zones:
            zid = z["zone_id"]
            w.writerow([zid, round(sol["uN"][zid], 4), round(sol["uK"][zid], 4)])
    else:
        w.writerow(["zone_id", "unmet_m3h"])
        for z in D.zones:
            zid = z["zone_id"]
            w.writerow([zid, round(sol["u"][zid], 4)])

    json.dump(summary, open(os.path.join(outdir, "solution_summary.json"),
                            "w", encoding="utf-8"), indent=2, ensure_ascii=False)

# DOĞRULAMA (tüm kısıtları kontrol ediliyor)
def is_feasible(D: Data, sol: dict, tol: float = 0.05) -> bool:
    """Tüm K1-K15 kısıtlarını verilen çözüm sözlüğü üzerinden doğrular."""
    T = T_PERIOD
    feasible = True

    x, q, w, y = sol["x"], sol["q"], sol["w"], sol["y"]
    t_plus, t_minus, V, u = sol["tp"], sol["tm"], sol["V"], sol["u"]

    def viol(msg: str):
        nonlocal feasible
        feasible = False
        log(f"[IHLAL] {msg}")

    def get_val(var_dict, key):
        if not isinstance(var_dict, dict): return 0.0
        v = var_dict.get(key, 0.0)
        return v.varValue if hasattr(v, "varValue") and v.varValue is not None else float(v)

    # K1, K2 - Kaynak Kapasite ve Taban Debi
    for s in D.sources:
        sid = s["source_id"]
        q_bar = float(s.get("capacity_m3h", 0.0))
        q_min = float(s.get("min_flow_if_active_m3h", 0.0))
        qs = get_val(q, sid)
        ws = int(round(get_val(w, sid)))
        if qs > q_bar * ws + tol:
            viol(f"K1: Kaynak {sid} q={qs:.2f} > Kapasite={q_bar * ws:.2f}")
        if ws == 1 and qs < q_min - tol:
            viol(f"K2: Kaynak {sid} q={qs:.2f} < MinDebi={q_min:.2f}")

    # K15 - Kaynak Paketleri
    for pkg in D.packages:
        pid = pkg["package_id"]
        max_act = int(pkg.get("max_active", len(pkg.get("member_source_ids", []))))
        toplam = sum(int(round(get_val(w, sid))) for sid in pkg.get("member_source_ids", []))
        if toplam > max_act:
            viol(f"K15: Kaynak Paketi {pid} Aktif={toplam} > Max={max_act}")

    # K3 - Ark Kapasitesi
    for a in D.arcs:
        aid = a["arc_id"]
        xa = get_val(x, aid)
        cap = D.arc_cap(a)
        if xa > cap + tol:
            viol(f"K3: Ark {aid} Debi={xa:.2f} > Kapasite={cap:.2f}")

    # K4, K5 - Pompa Kapasite ve Taban Debi
    for pmp in D.pumps:
        pid = pmp["pump_id"]
        f_bar = float(pmp.get("capacity_m3h", 0.0))
        f_min = float(pmp.get("min_flow_if_on", 0.0))
        yp = int(round(get_val(y, pid)))
        out_arcs = pmp.get("out_arc_ids", [])
        total_flow = sum(get_val(x, aid) for aid in out_arcs)
        if total_flow > f_bar * yp + tol:
            viol(f"K4: Pompa {pid} Debi={total_flow:.2f} > Kapasite={f_bar * yp:.2f}")
        if yp == 1 and total_flow < f_min - tol:
            viol(f"K5: Pompa {pid} Debi={total_flow:.2f} < MinDebi={f_min:.2f}")

    # K14 - Pompa Grupları
    for g in D.groups:
        gid = g["group_id"]
        max_act = int(g.get("max_active", len(g.get("member_pump_ids", []))))
        toplam = sum(int(round(get_val(y, pid))) for pid in g.get("member_pump_ids", []))
        if toplam > max_act:
            viol(f"K14: Pompa Grubu {gid} Aktif={toplam} > Max={max_act}")

    # K6 - Düğüm Akış Dengesi
    for n in D.nodes:
        nid = n["node_id"]
        gelen = sum(get_val(x, aid) for aid in D.node_in.get(nid, []))
        cikan = sum(get_val(x, aid) for aid in D.node_out.get(nid, []))
        kaynak_enj = get_val(q, D.src_at[nid]) if nid in D.src_at else 0.0
        depo_cekim  = get_val(t_minus, D.tank_at[nid]) if nid in D.tank_at else 0.0
        depo_dolum  = get_val(t_plus, D.tank_at[nid]) if nid in D.tank_at else 0.0

        karsilanan = 0.0
        if nid in D.zone_at:
            zid = D.zone_at[nid]
            dz = D.dz(zid)
            uz = get_val(u, zid)
            karsilanan = dz - uz

        lhs = gelen + kaynak_enj + depo_cekim
        rhs = cikan + depo_dolum + karsilanan
        if abs(lhs - rhs) > 1e-2:
            viol(f"K6: Düğüm {nid} Denge Hatası: Giren={lhs:.2f} != Çıkan={rhs:.2f}")

    # K7 - K10 Depo Seviye ve Dinamikleri
    for r in D.tanks:
        rid = r["tank_id"]
        V0 = float(r.get("initial_volume_m3", 0.0))
        V_bar = float(r.get("capacity_m3", 0.0))
        Vr = get_val(V, rid)
        tp = get_val(t_plus, rid)
        tm = get_val(t_minus, rid)

        beklenen_V = V0 + T * (tp - tm)
        if abs(Vr - beklenen_V) > 5e-2:
            viol(f"K7: Depo {rid} Hacim Hatası: V={Vr:.2f} != Beklenen={beklenen_V:.2f}")
        if Vr > V_bar + tol:
            viol(f"K8: Depo {rid} Taşma: V={Vr:.2f} > Kapasite={V_bar:.2f}")
        if T * tm > V0 + tol:
            viol(f"K9: Depo {rid} Çekim Limiti Aşıldı: {T * tm:.2f} > {V0:.2f}")
        if T * tp > V_bar + tol:
            viol(f"K10: Depo {rid} Dolum Limiti Aşıldı: {T * tp:.2f} > {V_bar:.2f}")

    total_demand_m3 = D.total_demand * T
    total_unmet_m3 = sum(get_val(u, z["zone_id"]) for z in D.zones) * T
    total_served_m3 = total_demand_m3 - total_unmet_m3
    service_rate = (total_served_m3 / total_demand_m3 * 100.0) if total_demand_m3 > 0 else 100.0

    log("\n" + "=" * 50)
    log("        KUANTUM / LP ÇÖZÜM DOĞRULAMA ÖZETİ        ")
    log("=" * 50)
    log(f" ÇÖZÜM FİZİBİL Mİ?           : {'EVET' if feasible else 'HAYIR (İHLAL VAR)'}")
    log(f" TALEP KARŞILAMA ORANI (%)   : %{service_rate:.2f}")
    log(f" Toplam Talep                : {total_demand_m3:,.2f} m3")
    log(f" Karşılanamayan Talep (u)    : {total_unmet_m3:,.2f} m3")
    log("=" * 50 + "\n")

    uN = sol.get("uN")
    uK = sol.get("uK")

    # ========================================================================
    # GÖREV 3 (PROBLEM 03) ÖZEL İHLAL VE MALİYET ANALİZİ
    # ========================================================================
    if D.problem == "problem_03" and uN is not None and uK is not None:
        tot_norm_dem_m3 = sum(D.dz_normal(z["zone_id"]) for z in D.zones) * T
        tot_crit_dem_m3 = sum(D.dz_critical(z["zone_id"]) for z in D.zones) * T

        unmet_norm_m3 = sum(get_val(uN, z["zone_id"]) for z in D.zones) * T
        unmet_crit_m3 = sum(get_val(uK, z["zone_id"]) for z in D.zones) * T

        cost_norm_penalty = unmet_norm_m3 * PI_TAL
        cost_crit_penalty = unmet_crit_m3 * (PI_TAL * 10.0)
        total_curtailment_cost = cost_norm_penalty + cost_crit_penalty

        norm_service_rate = (1.0 - unmet_norm_m3 / tot_norm_dem_m3) * 100.0 if tot_norm_dem_m3 > 0 else 100.0
        crit_service_rate = (1.0 - unmet_crit_m3 / tot_crit_dem_m3) * 100.0 if tot_crit_dem_m3 > 0 else 100.0

        cut_norm_zones = [z["zone_id"] for z in D.zones if get_val(uN, z["zone_id"]) > 1e-4]
        cut_crit_zones = [z["zone_id"] for z in D.zones if get_val(uK, z["zone_id"]) > 1e-4]

        log("-" * 60)
        log("          GÖREV 3: TALEP AYRIŞIMI VE CEZA MALİYETİ DÖKÜMÜ      ")
        log("-" * 60)
        log(f" [NORMAL TALEP]")
        log(f"   - Toplam Talep            : {tot_norm_dem_m3:,.2f} m3")
        log(f"   - Karşılanamayan (uN)     : {unmet_norm_m3:,.2f} m3 ({len(cut_norm_zones)} bölgede kesinti)")
        log(f"   - Karşılama Oranı         : %{norm_service_rate:.2f}")
        log(f"   - Birim Ceza Katsayısı    : {PI_TAL:,.0f} TL/m3")
        log(f"   - Normal Talep Ceza Tutarı: {cost_norm_penalty:,.2f} TL")
        log("")
        log(f" [KRİTİK TALEP]")
        log(f"   - Toplam Talep            : {tot_crit_dem_m3:,.2f} m3")
        log(f"   - Karşılanamayan (uK)     : {unmet_crit_m3:,.2f} m3 ({len(cut_crit_zones)} bölgede kesinti)")
        log(f"   - Karşılama Oranı         : %{crit_service_rate:.2f}")
        log(f"   - Birim Ceza Katsayısı    : {PI_TAL * 10.0:,.0f} TL/m3 (10x Öncelik)")
        log(f"   - Kritik Talep Ceza Tutarı: {cost_crit_penalty:,.2f} TL")
        log("-" * 60)
        log(f" TOPLAM KISINTI CEZA MALİYETİ: {total_curtailment_cost:,.2f} TL")
        
        if cut_crit_zones:
            log(f" [UYARI] Kritik talep kesintisi yapılan bölgeler: {cut_crit_zones}")
        else:
            log(f" [BAŞARILI] Hiçbir kritik bölgede su kesintisi yapılmadı (%100 karşılama).")


    # ========================================================================
    # GÖREV 4 (PROBLEM 04) ÖZEL ARIZA, İZOLASYON VE HASAR DENETİMİ
    # ========================================================================
    if D.problem == "problem_04":
        log("-" * 60)
        log("          GÖREV 4: ŞEBEKE HASAR VE ARIZA KONTROL RAPORU       ")
        log("-" * 60)

        # 1. Arızalı / Kullanılamaz Arklarda Akış Denetimi (K3)
        viol_failed_arcs = []
        for aid in D.unavailable:
            flow = get_val(x, aid)
            if flow > tol:
                viol_failed_arcs.append((aid, flow))
                viol(f"K3 (Hasar İhlali): Arızalı ark {aid} üzerinden debi akıyor! (x={flow:.4f} m3/sa)")

        log(f" [ŞEBEKE HASAR DURUMU]")
        log(f"   - Kullanılamayan Toplam Ark : {len(D.unavailable):,} adet")
        if viol_failed_arcs:
            log(f"   - [HATA] Akış Geçen Arızalı Ark Sayısı: {len(viol_failed_arcs)} adet!")
            for aid, fl in viol_failed_arcs[:5]:
                log(f"       * Ark {aid}: {fl:.2f} m3/sa debi")
            if len(viol_failed_arcs) > 5:
                log(f"       * ... ve {len(viol_failed_arcs) - 5} ark daha.")
        else:
            log(f"   - [BAŞARILI] Arızalı arkların hiçbirinden akış geçmiyor (Sıfır İhlal).")

        # 2. Arızadan Etkilenen Pompaların Denetimi (K4 / K5)
        impacted_pumps_on = []
        for pmp in D.pumps:
            pid = pmp["pump_id"]
            yp = int(round(get_val(y, pid)))
            if yp == 1:
                out_arcs = pmp.get("out_arc_ids", [])
                unav_outs = [aid for aid in out_arcs if aid in D.unavailable]
                if len(unav_outs) == len(out_arcs) and len(out_arcs) > 0:
                    impacted_pumps_on.append(pid)
                    viol(f"K4/K5 Çıkmazı: Pompa {pid} açık ancak tüm basma hatları arızalı!")

        log("")
        log(f" [TERFİ / POMPA ARIZA ETKİSİ]")
        log(f"   - Aktif Pompa Sayısı        : {sum(1 for p in D.pumps if get_val(y, p['pump_id']) > 0.5)} / {len(D.pumps)}")
        if impacted_pumps_on:
            log(f"   - [HATA] Çıkışı Tamamen Kapalı Olan Açık Pompalar: {impacted_pumps_on}")
        else:
            log(f"   - [BAŞARILI] Tüm açık pompaların en az bir basma hattı aktif.")

        # 3. Kısıntı ve Kıtlık Analizi
        unmet_zones = [z["zone_id"] for z in D.zones if get_val(u, z["zone_id"]) > 1e-4]
        total_unmet_vol = total_unmet_m3
        penalty_unmet = total_unmet_vol * PI_TAL

        log("")
        log(f" [TALEP VE KISINTI MALİYETİ]")
        log(f"   - Toplam Talep (24 Saat)    : {total_demand_m3:,.2f} m3")
        log(f"   - Karşılanamayan Miktar     : {total_unmet_vol:,.2f} m3")
        log(f"   - Şebeke Hizmet Oranı       : %{service_rate:.2f}")
        log(f"   - Kısıntı Yaşayan Bölge     : {len(unmet_zones)} / {len(D.zones)} bölge")
        log(f"   - Kısıntı Ceza Tutarı       : {penalty_unmet:,.2f} TL (Birim Ceza: {PI_TAL:,.0f} TL/m3)")

        # 4. Depo Güvenlik Seviyesi ve Acil Durum Desteği
        tanks_min_viol = [r["tank_id"] for r in D.tanks if get_val(sol.get("emin"), r["tank_id"]) > 1e-3]
        tanks_kri_viol = [r["tank_id"] for r in D.tanks if get_val(sol.get("ekri"), r["tank_id"]) > 1e-3]
        tanks_depleted = [r["tank_id"] for r in D.tanks if get_val(sol.get("etuk"), r["tank_id"]) > 1e-3]

        cost_emin = sum(get_val(sol.get("emin"), r["tank_id"]) for r in D.tanks) * PI_MIN
        cost_ekri = sum(get_val(sol.get("ekri"), r["tank_id"]) for r in D.tanks) * PI_KRI
        cost_etuk = sum(get_val(sol.get("etuk"), r["tank_id"]) for r in D.tanks) * PI_TUK

        log("")
        log(f" [DEPO STOKLARI VE SEVİYE İHLALLERİ]")
        log(f"   - Min Seviye Altına İnen Depolar    : {len(tanks_min_viol)} adet (Ceza: {cost_emin:,.2f} TL)")
        log(f"   - Kritik Seviye Altına İnen Depolar : {len(tanks_kri_viol)} adet (Ceza: {cost_ekri:,.2f} TL)")
        log(f"   - Başlangıç Seviyesini Koruyamayan  : {len(tanks_depleted)} adet (Fırsat Maliyeti: {cost_etuk:,.2f} TL)")
        log("-" * 60)
        log(f" TOPLAM CEZA VE FIRSAT MALİYETİ: {penalty_unmet + cost_emin + cost_ekri + cost_etuk:,.2f} TL")

    return feasible

# ANA AKIS
def run_problems_02_04(problem="problem_02", budget=300.0, data=".", token=os.getenv("DWAVE_API_TOKEN"), time_limit=10):
    t_start = time.time()
    deadline = t_start + budget
    left = lambda: deadline - time.time()
    outdir = problem

    log("=" * 66)
    log(" HIBRIT COZUM HATTI  |  %s  |  butce %.0f sn "
        % (problem, budget))
    log("=" * 66)

    log("[1/6] Veri okunuyor...")
    D = Data(data, problem)

    log("[2/6] Model kuruluyor (K1-K16)...")
    M = WaterModel(D)

    log("[3/6] LP gevsetmesi (CBC)...")
    M.relax()
    st, dt = M.solve(min(300, left() * 0.35))
    lp = M.read_solution()
    lp_bound = lp["true_obj"]
    core_w, core_y = fractional_core(lp)
    log("  durum=%s  |  %.1f sn  |  LP ALT SINIRI = %s TL"
        % (st, dt, format(lp_bound, ",.0f")))
    log("  kesirli cekirdek: %d kaynak + %d pompa = %d ikili  (toplam %d)"
        % (len(core_w), len(core_y), len(core_w) + len(core_y),
           len(D.sources) + len(D.pumps)))

    delta = marginal_costs(D, lp)

    log("[4/6] Kuantum adimi LeapHybridCQMSampler: cekirdek uzerinde CQM...")
    base_w = {k: (1 if v > 1 - 1e-6 else 0) for k, v in lp["w"].items()}
    base_y = {k: (1 if v > 1 - 1e-6 else 0) for k, v in lp["y"].items()}

    free_w, free_y = list(core_w), list(core_y)
    warm_w, warm_y = dict(base_w), dict(base_y)
    anneal_calls = 0
    try:
        extra = sorted([p["pump_id"] for p in D.pumps if p["pump_id"] not in core_y],
                       key=lambda pid: abs(delta.get(pid, 0.0)))[:150]
        pool_y = list(core_y) + extra
        samples = []
        for aux in (True, False):
            try:
                cqm = build_cqm(D, base_w, base_y, free_w, pool_y, delta, lp, aux=aux)
                samples = sample_cqm(cqm, token, time_limit=time_limit)
                anneal_calls += 1
                break
            except Exception as e:
                log("  ! CQM (aux=%s) basarisiz: %s" % (aux, str(e)[:90]))
        if samples:
            warm_w, warm_y = apply_sample(base_w, base_y, samples[0])
            warm_w, warm_y = repair_groups(D, warm_w, warm_y, delta)
            for pid in pool_y:
                if warm_y.get(pid, 0) != base_y.get(pid, 0) and pid not in free_y:
                    free_y.append(pid)
        log("  %d ornek | serbest kume: %d pompa + %d kaynak = %d ikili"
            % (len(samples), len(free_y), len(free_w), len(free_y) + len(free_w)))
    except Exception as e:
        log("  ! tavlama atlandi (%s) -> yalnizca LP cekirdegi kullanilacak" % e)

    log("[5/6] CBC dal-sinir (serbest %d ikili)..." % (len(free_y) + len(free_w)))
    M.set_integer(free_w, free_y, base_w, base_y)
    warm_ok = M.warm_start(warm_w, warm_y)
    mip_budget = max(60.0, left() - 90.0)
    st, dt = M.solve(mip_budget, gap=0.03, warm=warm_ok)
    best = M.read_solution()
    log("  durum=%s | %s TL | pompa %d | karsilama %%%.2f | ihlal %.4f | %.0f sn"
        % (st, format(best["true_obj"], ",.0f"), best["n_pumps_on"],
           best["service_rate"], best["slack_total"], dt))

    best_w = {k: int(round(v)) for k, v in best["w"].items()}
    best_y = {k: int(round(v)) for k, v in best["y"].items()}
    it = 1
    accepted = 1 if is_admissible(best) else 0

    repair_round = 0
    while (not is_admissible(best)) and left() > 120 and repair_round < 2:
        repair_round += 1
        if repair_round == 1:
            free_w, free_y, added = expand_free_set(D, best, free_w, free_y)
            if added == 0:
                repair_round = 2
        if repair_round == 2:
            free_w = [s["source_id"] for s in D.sources]
            free_y = [p["pump_id"] for p in D.pumps]
        log("  [onarim %d] ihlal %.2f -> serbest kume %d ikili"
            % (repair_round, best["slack_total"], len(free_y) + len(free_w)))
        M.set_integer(free_w, free_y, base_w, base_y)
        M.warm_start(best_w, best_y)
        st, dt = M.solve(max(90.0, left() - 80.0), gap=0.06, warm=True)
        cand = M.read_solution()
        log("    durum=%s | %s TL | pompa %d | ihlal %.4f | %.0f sn"
            % (st, format(cand["true_obj"], ",.0f"), cand["n_pumps_on"],
               cand["slack_total"], dt))
        if cand["slack_total"] < best["slack_total"] - 1e-6 or \
           (is_admissible(cand) and not is_admissible(best)):
            best = cand
            best_w = {k: int(round(v)) for k, v in cand["w"].items()}
            best_y = {k: int(round(v)) for k, v in cand["y"].items()}
            accepted += 1
        if is_admissible(best):
            break

    if left() > 200 and is_admissible(best):
        try:
            delta2 = marginal_costs(D, best)
            pool2 = list(free_y) + sorted(
                [p["pump_id"] for p in D.pumps if p["pump_id"] not in free_y],
                key=lambda pid: abs(delta2.get(pid, 0.0)))[:150]
            smp2 = []
            for aux in (True, False):
                try:
                    cqm2 = build_cqm(D, best_w, best_y, free_w, pool2, delta2, best, aux=aux)
                    smp2 = sample_cqm(cqm2, token, time_limit=time_limit)
                    anneal_calls += 1
                    break
                except Exception as e:
                    log("  ! CQM tur2 (aux=%s): %s" % (aux, str(e)[:90]))
            if smp2:
                w2, y2 = apply_sample(best_w, best_y, smp2[0])
                w2, y2 = repair_groups(D, w2, y2, delta2)
                fy2 = list(free_y)
                for pid in pool2:
                    if y2.get(pid, 0) != best_y.get(pid, 0) and pid not in fy2:
                        fy2.append(pid)
                M.set_integer(free_w, fy2, best_w, best_y)
                M.warm_start(w2, y2)
                st, dt = M.solve(max(60.0, left() - 90.0), gap=0.02, warm=True)
                cand = M.read_solution()
                better = is_admissible(cand) and cand["true_obj"] < best["true_obj"] - 1e-3
                log("  tur 2 | %s TL | pompa %d | %s (%.0f sn)"
                    % (format(cand["true_obj"], ",.0f"), cand["n_pumps_on"],
                       "KABUL" if better else "red", dt))
                it = 2
                if better:
                    best = cand
                    best_w = {k: int(round(v)) for k, v in cand["w"].items()}
                    best_y = {k: int(round(v)) for k, v in cand["y"].items()}
                    accepted += 1
        except Exception as e:
            log("  ! tur 2 atlandi: %s" % e)

    # Doğrulama Kontrolü
    final = best
    feas_check = is_feasible(D, final)

    gap = (100.0 * (final["true_obj"] - lp_bound) / abs(lp_bound)) if lp_bound else 0.0
    summary = {
        "problem_id": problem,
        "objective_value": round(final["true_obj"], 2),
        "lp_lower_bound":  round(lp_bound, 2),
        "optimality_gap_pct": round(gap, 2),
        "runtime_sec": round(time.time() - t_start, 2),
        "method": "LP relaxation (PuLP/CBC) -> fractional core -> "
                  "dual-guided CQM -> D-Wave annealing -> CBC verification (Q-LNS)",
        "sampler": "LeapHybridCQMSampler",
        "anneal_calls": anneal_calls,
        "lns_rounds": it,
        "accepted_moves": accepted,
        "repair_rounds": repair_round,
        "core_size": len(core_w) + len(core_y),
        "n_sources_active": final["n_sources_on"],
        "n_pumps_on": final["n_pumps_on"],
        "unmet_demand_m3h": round(final["unmet_total"], 4),
        "service_rate_pct": round(final["service_rate"], 4),
        "min_flow_violation": round(final["slack_total"], 6),
        "feasible": bool(is_admissible(final) and feas_check),
        "penalty_weights": {"Pi_tal": PI_TAL, "Pi_min": PI_MIN, "Pi_kri": PI_KRI,
                            "Pi_tuk": PI_TUK, "rho": RHO, "tau": TAU,
                            "sigma_hed": SIGMA_HED},
    }

    log("[6/6] Gonderi dosyalari yaziliyor -> %s/" % outdir)
    export(D, final, outdir, summary)

    log("=" * 66)
    log(" AMAC DEGERI     : %s TL" % format(final["true_obj"], ",.2f"))
    log(" LP ALT SINIRI   : %s TL   (gap %%%.2f)" % (format(lp_bound, ",.2f"), gap))
    log(" ACIK POMPA      : %d / %d" % (final["n_pumps_on"], len(D.pumps)))
    log(" ACIK KAYNAK     : %d / %d" % (final["n_sources_on"], len(D.sources)))
    log(" KARSILAMA       : %%%.4f  (karsilanamayan %.3f m3/sa)"
        % (final["service_rate"], final["unmet_total"]))
    log(" K2/K5 IHLALI    : %.6f   -> %s"
        % (final["slack_total"], "UYGUN" if is_admissible(final) else "UYGUN DEGIL"))
    log(" GENEL UYGUNLUK  : %s" % ("EVET" if feas_check else "HAYIR"))
    log(" TOPLAM SURE     : %.1f sn" % (time.time() - t_start))
    log("=" * 66)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", default="problem_01", choices=["problem_01", "problem_02", "problem_03", "problem_04"])
    ap.add_argument("--data", default=".")
    ap.add_argument("--token", default=os.getenv("DWAVE_API_TOKEN"))
    ap.add_argument("--budget", type=float, default=300.0)
    ap.add_argument("--time_limit", type=int, default=10)
    args = ap.parse_args()

    if args.problem == "problem_01":
        run_problem_01(args.token)
    else:
        run_problems_02_04(problem=args.problem, budget=args.budget, data=args.data, token=args.token, time_limit=args.time_limit)


if __name__ == "__main__":
    main()
