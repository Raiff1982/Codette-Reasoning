import sys
import time
import numpy as np
import networkx as nx

def path_to_edge_set(path):
    """Converts a node path sequence into a frozen set of normalized edges."""
    edges = []
    for i in range(len(path)):
        u, v = path[i], path[(i + 1) % len(path)]
        edges.append(tuple(sorted((u, v))))
    return frozenset(edges)

def expand_cycle_pool(basis, target_count=400):
    """
    Applies symmetric differences (XOR) directly to EDGE sets to expand the basis.
    Uses a clean Eulerian network walker to reconstruct true, simple physical cycles.
    """
    pool_edges = set()
    pure_pool = []
    
    # Initialize pool with the fundamental basis
    for path in basis:
        eset = path_to_edge_set(path)
        if len(eset) >= 3 and eset not in pool_edges:
            pool_edges.add(eset)
            pure_pool.append(path)

    # Generational edge-XOR expansion layer
    basis_edge_sets = list(pool_edges)
    
    for i in range(len(basis_edge_sets)):
        if len(pure_pool) >= target_count:
            break
        for j in range(i + 1, len(basis_edge_sets)):
            if len(pure_pool) >= target_count:
                break
                
            e1, e2 = basis_edge_sets[i], basis_edge_sets[j]
            xor_edges = e1.symmetric_difference(e2)
            
            if len(xor_edges) >= 3 and xor_edges not in pool_edges:
                # Build local adjacency map from the raw edge set
                adj = {}
                for u, v in xor_edges:
                    adj.setdefault(u, []).append(v)
                    adj.setdefault(v, []).append(u)
                
                # Check Eulerian condition: every vertex must have an even degree
                if any(len(neighbors) % 2 != 0 for neighbors in adj.values()):
                    continue
                
                # Manually walk the loop to reconstruct a clean node sequence
                try:
                    start_node = next(iter(adj))
                    path = [start_node]
                    curr = adj[start_node][0]
                    prev = start_node
                    
                    while curr != start_node:
                        path.append(curr)
                        next_nodes = [n for n in adj[curr] if n != prev]
                        if not next_nodes:
                            raise ValueError
                        prev, curr = curr, next_nodes[0]
                    
                    if len(path) >= 3:
                        pool_edges.add(xor_edges)
                        pure_pool.append(path)
                except (StopIteration, ValueError, IndexError):
                    continue
                        
    return pure_pool[:target_count]

def build_cycle_matrix(G, cycles):
    """Maps topological cycles to a clean, flat binary matrix array."""
    edges = list(G.edges())
    edge_to_idx = {tuple(sorted(e)): i for i, e in enumerate(edges)}
    
    matrix = np.zeros((len(cycles), len(edges)), dtype=np.int8)
    for c_idx, cycle in enumerate(cycles):
        for i in range(len(cycle)):
            u, v = cycle[i], cycle[(i + 1) % len(cycle)]
            e = tuple(sorted((u, v)))
            if e in edge_to_idx:
                matrix[c_idx, edge_to_idx[e]] = 1
    return matrix, edges

def find_fundamental_cycles(G):
    """Extracts the base non-recursive fundamental cycle basis via a spanning tree."""
    tree = nx.minimum_spanning_tree(G)
    non_tree_edges = [e for e in G.edges() if not tree.has_edge(*e)]
    
    basis = []
    for u, v in non_tree_edges:
        path = nx.shortest_path(tree, source=u, target=v)
        basis.append(path)
    return basis

def run_iterative_dfs(cycle_matrix, num_edges):
    """
    Zero-allocation, in-place backtracking DFS engine.
    Eliminates all array copying and list recreation for extreme speed.
    """
    num_cycles = cycle_matrix.shape[0]
    
    # Global mutable state tracking (single static memory allocations)
    coverage = np.zeros(num_edges, dtype=np.int8)
    chosen = []
    
    # Stack tracks execution frame states: (cycle_index, action_step)
    # Action steps:
    # 0: Evaluate inclusion / proceed forward
    # 2: Backtrack (subtract cycle and restore previous state)
    stack = [(0, 0)]
    
    states_evaluated = 0
    start_time = time.time()
    
    print("\n🧠 [Reasoning] Launching active DFS pruning engine over iterative structure...")
    
    while stack:
        c_idx, step = stack.pop()
        
        # Base case: reached end of cycle options
        if c_idx >= num_cycles:
            continue
            
        if step == 0:
            states_evaluated += 1
            if states_evaluated % 5000000 == 0:
                elapsed = time.time() - start_time
                rate = states_evaluated / elapsed / 1000000
                print(f"🔍 [Steering] Evaluated {states_evaluated:,} states... "
                      f"Active Path Depth: {len(chosen)} | Speed: {rate:.2f}M states/sec")
            
            # Fast target check: check if all values are exactly 2
            if np.all(coverage == 2):
                print(f"\n🎉 [Success] Valid Cycle Double Cover isolated at state {states_evaluated:,}!")
                return list(chosen)

            cycle_vector = cycle_matrix[c_idx]
            
            # Inline check: can we add this cycle without hitting 3 anywhere?
            # Doing this calculation inline prevents unnecessary array allocations.
            if np.max(coverage + cycle_vector) <= 2:
                # Apply mutations in-place
                coverage += cycle_vector
                chosen.append(c_idx)
                
                # Push the backtrack step first, then advance to next cycle index
                stack.append((c_idx, 2))
                stack.append((c_idx + 1, 0))
            else:
                # Cannot include. Jump directly to skipping this cycle index.
                stack.append((c_idx + 1, 0))

        elif step == 2:
            # Backtrack action: cleanly reverse the in-place operation
            cycle_vector = cycle_matrix[c_idx]
            coverage -= cycle_vector
            chosen.pop()
            
            # Explore the alternative branch where this cycle is skipped
            stack.append((c_idx + 1, 0))

    print(f"\n🏁 Search space fully exhausted at {states_evaluated:,} states. No valid double cover within this basis.")
    return None

if __name__ == "__main__":
    print("ℹ️ Initializing 40-vertex random cubic graph skeleton...")
    G = nx.random_regular_graph(d=3, n=40, seed=42)
    
    # Generate hyper-pure cycles using edge-XOR
    print("🧠 [Reasoning] Extracting fundamental cycle framework...")
    base_basis = find_fundamental_cycles(G)
    robust_pool = expand_cycle_pool(base_basis, target_count=400)
    
    matrix, edge_list = build_cycle_matrix(G, robust_pool)
    print(f"ℹ️ Mapped {len(edge_list)} edges into {matrix.shape[0]} robust, non-recursive cycles.")
    
    try:
        solution = run_iterative_dfs(matrix, len(edge_list))
    except KeyboardInterrupt:
        print("\n🛑 Execution paused by user safety override. Pipeline state secure.")