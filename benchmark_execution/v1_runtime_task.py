from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import yaml


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def task_record(image_manifest: dict, task_id: str) -> dict:
    matches = [x for x in image_manifest["tasks"] if x["task_id"] == task_id]
    if len(matches) != 1:
        raise RuntimeError(f"V1_TASK_IMAGE_RECORD_UNRESOLVED:{task_id}:{len(matches)}")
    return matches[0]


def assemble(source_task: Path, destination: Path, record: dict) -> dict:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source_task, destination)

    task_toml = destination / "task.toml"
    text = task_toml.read_text(encoding="utf-8")
    if "docker_image" in text:
        raise RuntimeError("V1_RUNTIME_TASK_UNEXPECTED_EXISTING_DOCKER_IMAGE")
    marker = "[environment]\n"
    if text.count(marker) != 1:
        raise RuntimeError("V1_RUNTIME_TASK_ENVIRONMENT_SECTION_INVALID")
    main_ref = record["primary_main_immutable_image_reference"]
    text = text.replace(marker, marker + f'docker_image = "{main_ref}"\n', 1)
    task_toml.write_text(text, encoding="utf-8")

    compose_path = destination / "environment/docker-compose.yaml"
    compose_services = {}
    if compose_path.exists():
        compose = yaml.safe_load(compose_path.read_text(encoding="utf-8")) or {}
        services = compose.setdefault("services", {})
        for service, immutable_ref in record["service_identity"].items():
            service_cfg = services.setdefault(service, {})
            service_cfg.pop("build", None)
            service_cfg["image"] = immutable_ref
            compose_services[service] = immutable_ref
        for service, cfg in services.items():
            if "build" in cfg:
                raise RuntimeError(f"V1_RUNTIME_TASK_UNPINNED_BUILD:{service}")
            if service in record["service_identity"] and cfg.get("image") != record["service_identity"][service]:
                raise RuntimeError(f"V1_RUNTIME_TASK_SERVICE_IMAGE_MISMATCH:{service}")
        compose_path.write_text(yaml.safe_dump(compose, sort_keys=False), encoding="utf-8")
    elif set(record["service_identity"]) != {"main"}:
        raise RuntimeError("V1_RUNTIME_TASK_COMPOSE_MISSING_FOR_MULTISERVICE_BUNDLE")

    provenance = {
        "schema_version": 1,
        "experiment_version": "v1-environment-materialized",
        "task_id": record["task_id"],
        "task_environment_source_identity_sha256": record["task_environment_source_identity_sha256"],
        "task_environment_bundle_sha256": record["task_environment_bundle_sha256"],
        "primary_main_immutable_image_reference": main_ref,
        "service_identity": record["service_identity"],
        "per_condition_rebuild_forbidden": True,
        "runtime_compose_service_overrides": compose_services,
    }
    (destination / ".v1-runtime-materialization.json").write_text(canon(provenance), encoding="utf-8")
    return provenance


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image-manifest", type=Path, required=True)
    ap.add_argument("--source-task", type=Path, required=True)
    ap.add_argument("--destination", type=Path, required=True)
    ap.add_argument("--task", required=True)
    args = ap.parse_args()
    manifest = json.loads(args.image_manifest.read_text(encoding="utf-8"))
    rec = task_record(manifest, args.task)
    provenance = assemble(args.source_task, args.destination, rec)
    print(f"V1_RUNTIME_TASK_ASSEMBLED task={args.task} bundle={provenance['task_environment_bundle_sha256']}")
    print("PER_CONDITION_REBUILD=FORBIDDEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
