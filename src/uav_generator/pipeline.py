# uav_generator/pipeline.py
import shutil
from pathlib import Path
from .data_models import ProjectInput, DerivedDesign, BlockingIssue

# Import calculator modules (will be created next)
from .calculators import mass, aerodynamics, propulsion, ground, control_system

# Import exporter modules
from .exporters import jsbsim_writer, report_writer, flightgear

class PipelineOrchestrator:
    """
    Drives the entire UAV design and generation process.
    """
    def __init__(self, project_input: ProjectInput, output_dir: Path):
        self.project_input = project_input
        self.output_dir = output_dir
        self.design = DerivedDesign()

    def run(self) -> bool:
        """
        Executes the design pipeline step-by-step.
        
        Returns:
            bool: True if generation was successful, False if blocking issues were found.
        """
        print("\nINFO: Starting design pipeline...")

        # 1. Run calculation blocks in sequence
        print("INFO: [1/5] Calculating mass budget...")
        self.design = mass.calculate_mass_budget(self.project_input, self.design)

        print("INFO: [2/5] Synthesizing control system (FCS)...")
        self.design = control_system.calculate_control_system(self.project_input, self.design)

        print("INFO: [3/5] Calculating aerodynamics and surfaces...")
        self.design = aerodynamics.calculate_aero(self.project_input, self.design)

        print("INFO: [4/6] Calculating vertical geometry...")
        from .calculators.vertical_geometry_solver import calculate_vertical_geometry
        self.design = calculate_vertical_geometry(self.project_input, self.design)
        
        print("INFO: [5/6] Calculating propulsion...")
        self.design = propulsion.calculate_propulsion(self.project_input, self.design)
        
        print("INFO: [6/6] Calculating ground interactions...")
        self.design = ground.calculate_ground_systems(self.project_input, self.design)

        print("INFO: Validating FCS and Aerodynamics contract...")
        self.design = control_system.validate_fcs_contract(self.design)

        # 2. Check for blocking issues
        if self.design.blocking_issues:
            self._report_blocking_issues()
            # In a future version, we could trigger the auto-correction loop here.
            return False

        # 3. If successful, run exporters
        print("\nINFO: All calculations successful. Proceeding to export...")
        
        self._run_exporters()

        return True

    def _report_blocking_issues(self):
        """Prints a summary of all detected blocking issues."""
        print("\n" + "="*60)
        print("FATAL: Blocking issues prevent UAV generation.")
        print("Please review and address the following problems:")
        print("="*60)
        for issue in self.design.blocking_issues:
            print(f"\n- ISSUE CODE: {issue.code}")
            print(f"  CAUSE: {issue.cause}")
            print("  PROPOSED FIXES:")
            for i, proposal in enumerate(issue.proposals, 1):
                print(f"    {i}. {proposal.description}")
                # print(f"       (Apply with: {proposal.apply_changes})")
        print("\n" + "="*60)
        
    def _run_exporters(self):
        """
        Generates all output files.
        """
        # Create a single, unified output directory for the UAV package, as per prompt.txt
        uav_name = self.project_input.projet.nom
        # This will create an `output` folder in the project root, containing the UAV package.
        uav_package_dir = self.output_dir / "output" / uav_name
        
        # CORRECTION 1: Purge existing directory to prevent ghost files
        if uav_package_dir.exists():
            shutil.rmtree(uav_package_dir)
        
        # Create all necessary directories
        uav_package_dir.mkdir(parents=True, exist_ok=True)
        (uav_package_dir / "Engines").mkdir(exist_ok=True)
        (uav_package_dir / "Models").mkdir(exist_ok=True)
        (uav_package_dir / "Systems").mkdir(exist_ok=True)
        (uav_package_dir / "Nasal").mkdir(exist_ok=True)
        (uav_package_dir / "Docs").mkdir(exist_ok=True)
        # Remove Sounds/ if exists (per task)
        sounds_dir = uav_package_dir / "Sounds"
        if sounds_dir.exists():
            shutil.rmtree(sounds_dir)
            print("INFO: Removed existing Sounds/ directory.")
        # The "Reports" directory will be created by the report_writer inside the package.
        
        print(f"INFO: Generating UAV package in {uav_package_dir}")

        # Generate all files inside this single, consolidated package directory
        jsbsim_writer.generate_jsbsim_package(self.project_input, self.design, uav_package_dir)
        report_writer.generate_reports(self.project_input, self.design, uav_package_dir)
        
        # Final step: copy to FlightGear
        flightgear.copy_to_flightgear(uav_package_dir)
