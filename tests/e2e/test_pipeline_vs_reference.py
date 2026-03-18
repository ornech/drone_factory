from pathlib import Path
import yaml
from uav_generator.pipeline import PipelineOrchestrator
from uav_generator.data_models import ProjectInput
import filecmp


def test_pipeline_matches_reference(tmp_path):
    root = Path(__file__).resolve().parents[2]
    spec = root / "external" / "drone_spec"

    yaml_path = spec / "fixtures" / "uav_obs_01_ref" / "project.yaml"
    reference = spec / "references" / "uav_obs_01"

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    project_input = ProjectInput(**data)

    orchestrator = PipelineOrchestrator(project_input, tmp_path)
    success = orchestrator.run()

    assert success, "Pipeline a échoué"

    generated = tmp_path / "output" / "uav_obs_01"

    expected_files = [
        "JSBSim/uav_obs_01.xml",
        "uav_obs_01-set.xml",
        "Models/uav_obs_01.ac",
        "Models/uav_obs_01-model.xml",
        "Systems/flight-control.xml",
        "Reports/derived_design.json",
    ]

    for rel in expected_files:
        gen_file = generated / rel
        ref_file = reference / rel

        assert gen_file.exists(), f"Manquant: {gen_file}"
        assert ref_file.exists(), f"Reference manquante: {ref_file}"

        assert filecmp.cmp(gen_file, ref_file, shallow=False), \
            f"Différence détectée sur {rel}"
