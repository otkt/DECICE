from copy import deepcopy
from itertools import product
from typing import List, Set

from models.models import (ClusterState, Link, Node, ScheduleRequest, Task,
                           Vertexpool)

REQUIRED_ANNOTATION_KEYS = [
    "network.dev.decice.com/used-device-names",
    "network.dev.decice.com/total-max-latency-ms",
]


def get_device_names_from_task(task: Task) -> List[str]:
    """
    Extract device names from task annotations, if present.
    """
    if not task.annotations:
        return []
    
    r =task.annotations.get("network.dev.decice.com/used-device-names", [])
    print(f"Extracted related device names from task {task.id}: {r}")
    return r


def calculate_total_latency(
    node_name: str,
    device_names: List[str],
    links: List[Link],
    vertexpools: List[Vertexpool],
) -> float:
    """
    Calculate total latency between a node and all specified devices.
    """
    device_to_vertexpool = {}
    node_to_vertexpool = {}

    # Map device names to their vertexpool IDs
    for vp in vertexpools:
        for device in vp.devices:
            if device.name in device_names:
                device_to_vertexpool[device.name] = vp.id
        for node in vp.nodes:
            node_to_vertexpool[node.name] = vp.id

    total_latency = 0.0
    node_vp_id = node_to_vertexpool.get(node_name)
    if not node_vp_id:
        # Node not found in any vertexpool
        return float("inf")

    for device_name in device_names:
        device_vp_id = device_to_vertexpool.get(device_name)
        if not device_vp_id:
            # Device not found
            total_latency += float("inf")
            continue

        if device_vp_id == node_vp_id:
            # Same vertexpool: latency assumed 0
            continue

        # Find link latency
        link_latency = next(
            (
                link.network_delay_ms
                for link in links
                if {link.vertexpool_a_id, link.vertexpool_b_id}
                == {node_vp_id, device_vp_id}
            ),
            float("inf"),  # No link -> infinite latency
        )
        total_latency += link_latency

    return total_latency


def filter_nodes_by_latency(
    nodes: List[Node], task: Task, cluster_state: ClusterState
) -> List[Node]:
    """
    Return nodes where total latency to all required devices is <= max allowed.
    """
    if task.annotations is None:
        return nodes

    max_latency = task.annotations.get(
        "network.dev.decice.com/total-max-latency-ms", None
    )
    if max_latency is None:
        return nodes
    try:
        max_latency = float(max_latency)
    except (ValueError, TypeError):
        return nodes

    device_names = get_device_names_from_task(task)
    if not device_names:
        return nodes

    filtered_nodes = []
    for node in nodes:
        total_latency = calculate_total_latency(
            node.name, device_names, cluster_state.links, cluster_state.vertexpools
        )
        if total_latency <= max_latency:
            filtered_nodes.append(node)

    return filtered_nodes


def filter_schedule_request_by_device_latency(
    schedule_request: ScheduleRequest,
) -> ScheduleRequest:
    """
    Returns a new ScheduleRequest with nodes filtered based on latency constraints
    from task annotations. Only keeps nodes that satisfy all tasks.
    If not tasks has the network annotations, returns the original ScheduleRequest
    """
    cluster_state = schedule_request.cluster
    all_nodes = [node for vp in cluster_state.vertexpools for node in vp.nodes]

    # Step 0: Pre-filter tasks without required annotations
    tasks_with_annotations = []
    for task in schedule_request.tasks:
        if task.annotations and all(
            key in task.annotations for key in REQUIRED_ANNOTATION_KEYS
        ):
            tasks_with_annotations.append(task)

    # If no task has the required annotations, return the original ScheduleRequest
    if not tasks_with_annotations:
        return schedule_request

    # Step 1: Filter nodes per task
    task_to_nodes: list[Set[str]] = []
    for task in schedule_request.tasks:
        filtered_nodes = filter_nodes_by_latency(all_nodes, task, cluster_state)
        node_names = set(node.name for node in filtered_nodes)
        task_to_nodes.append(node_names)

    # Step 2: Take intersection across all tasks
    if task_to_nodes:
        intersection_nodes = set.intersection(*task_to_nodes)
    else:
        intersection_nodes = set()

    # Step 3: Deepcopy cluster state and remove filtered out nodes
    filtered_cluster = deepcopy(cluster_state)
    for vp in filtered_cluster.vertexpools:
        vp.nodes = [node for node in vp.nodes if node.name in intersection_nodes]

    # Step 4: Return a new ScheduleRequest
    return ScheduleRequest(tasks=schedule_request.tasks, cluster=filtered_cluster)
