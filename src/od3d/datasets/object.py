import logging

logger = logging.getLogger(__name__)
from od3d.datasets.meta import OD3D_Meta
from abc import ABC
from dataclasses import dataclass
from pathlib import Path
import torch
from od3d.data.ext_enum import StrEnum
from typing import List
from od3d.cv.geometry.objects3d.meshes import Meshes

# from od3d.datasets.frame import OD3D_FRAME_MODALITIES


@dataclass
class OD3D_Object(ABC):
    name_unique: str
    path_raw: Path
    path_preprocess: Path
    meta_type = OD3D_Meta

    @property
    def meta(self):
        return self.meta_type.load_from_meta_with_name_unique(
            path_meta=self.path_meta,
            name_unique=self.name_unique,
        )

    @property
    def name(self):
        return self.meta.name

    @property
    def path_meta(self):
        return self.path_preprocess.joinpath("meta")


class OD3D_CAM_TFORM_OBJ_TYPES(StrEnum):
    META = "meta"
    SFM = "sfm"


class OD3D_FRAME_MASK_TYPES(StrEnum):
    META = "meta"
    SAM = "sam"
    MESH = "mesh"
    SAM_SFM_RAYS_CENTER3D = "sam_sfm_rays_center3d"
    SAM_KPTS2D = "sam_kpts2d"
    SAM_BBOX = "sam_bbox"
    SAM_KPTS2D_BBOX = "sam_kpts2d_bbox"


class OD3D_FRAME_DEPTH_TYPES(StrEnum):
    META = "meta"
    MESH = "mesh"


class OD3D_SCALE_TYPES(StrEnum):
    REAL = "real"
    NORM = "norm"


class OD3D_MESH_TYPES(StrEnum):
    META = "meta"
    CONVEX500 = "convex500"
    ALPHA500 = "alpha500"
    CUBOID250 = "cuboid250"
    CUBOID500 = "cuboid500"
    CUBOID1000 = "cuboid1000"
    SPHERE250 = "sphere250"
    SPHERE500 = "sphere500"
    SPHERE1000 = "sphere1000"
    TRELLIS500 = "trellis500"
    TRELLISMASK500 = "trellismask500"
    TRELLISMV500 = "trellismv500"
    TRELLISMVMASK500 = "trellismvmask500"


class OD3D_MESH_FEATS_TYPES(StrEnum):
    M_DINOV2_VITS14_FROZEN_BASE_NO_NORM_T_CENTERZOOM512_R_ACC = (
        "M_dinov2_vits14_frozen_base_no_norm_T_centerzoom512_R_acc"
    )
    M_DINOV2_VITB14_FROZEN_BASE_NO_NORM_T_CENTERZOOM512_R_ACC = (
        "M_dinov2_vitb14_frozen_base_no_norm_T_centerzoom512_R_acc"
    )
    M_DINOV2_FROZEN_BASE_NO_NORM_T_CENTERZOOM512_R_ACC = (
        "M_dinov2_frozen_base_no_norm_T_centerzoom512_R_acc"
    )
    M_DINOV2_FROZEN_BASE_T_CENTERZOOM512_R_ACC = (
        "M_dinov2_frozen_base_T_centerzoom512_R_acc"
    )
    M_DINO_VITS8_FROZEN_BASE_NO_NORM_T_CENTERZOOM512_R_ACC = (
        "M_dino_vits8_frozen_base_no_norm_T_centerzoom512_R_acc"
    )
    M_RESNET50_FROZEN_BASE_NO_NORM_T_CENTERZOOM512_R_ACC = (
        "M_resnet50_frozen_base_no_norm_T_centerzoom512_R_acc"
    )
    M_NEMO_OLD_T_CENTERZOOM512_R_ACC = "M_nemo_old_T_centerzoom512_R_acc"


class OD3D_MESH_FEATS_DIST_REDUCE_TYPES(StrEnum):
    AVG = "avg"
    NEGDOT_AVG = "negdot_avg"
    AVG50 = "avg50"
    NEGDOT_AVG50 = "negdot_avg50"
    MIN = "min"
    NEGDOT_MIN = "negdot_min"
    MIN_AVG = "min_avg"
    NEGDOT_MIN_AVG = "negdot_min_avg"


class OD3D_PCL_TYPES(StrEnum):
    META = "meta"
    KEYPOINTS = "keypoints"
    META_MASK = "meta_mask"
    SFM = "sfm"
    SFM_MASK = "sfm_mask"
    POISSON_DISK = "poisson_disk"
    POISSON_DISK_FPS = "poisson_disk_fps"


class OD3D_TFROM_OBJ_TYPES(StrEnum):
    RAW = "raw"
    CENTER3D_AUTO = "center3d_auto"
    CENTER3D = "center3d"
    LABEL3D_ZSP = "label3d_zsp"
    LABEL3D_ZSP_CUBOID = "label3d_zsp_cuboid"
    LABEL3D = "label3d"
    LABEL3D_CUBOID = "label3d_cuboid"
    META = "meta"
    META_CUBOID = "meta_cuboid"

    # ALIGNED7D = 'aligned7d'


class OD3D_SEQUENCE_SFM_TYPES(StrEnum):
    META = "meta"
    DROID = "droid"
    COLMAP = "colmap"


class OD3D_FRAME_KPTS2D_ANNOT_TYPES(StrEnum):
    META = "meta"
    LABEL = "label"


@dataclass
class OD3D_FrameKpts2d3dTypeMixin(OD3D_Object):
    kpts2d_annot_type: OD3D_FRAME_KPTS2D_ANNOT_TYPES


@dataclass
class OD3D_TformObjMixin:
    tform_obj_type: OD3D_TFROM_OBJ_TYPES

    def get_tform_obj(self, tform_obj_type: OD3D_TFROM_OBJ_TYPES = None, device="cpu"):
        if tform_obj_type is None:
            tform_obj_type = self.tform_obj_type

        if tform_obj_type == OD3D_TFROM_OBJ_TYPES.CENTER3D_AUTO:
            return torch.eye(4)
        else:
            fpath_tform_obj = self.get_fpath_tform_obj(tform_obj_type=tform_obj_type)
            if fpath_tform_obj.exists():
                return torch.load(
                    self.get_fpath_tform_obj(tform_obj_type=tform_obj_type),
                ).to(device=device)
            else:
                logger.warning(
                    f"tform_obj_type {tform_obj_type} does not exists at {fpath_tform_obj}",
                )
                return None

    def get_fpath_tform_obj(self, tform_obj_type=None):
        raise NotImplementedError

    def write_tform_obj(self, tform_obj: torch.Tensor, fpath_tform_obj=None):
        if fpath_tform_obj is None:
            fpath_tform_obj = self.get_fpath_tform_obj()
        if fpath_tform_obj.parent.exists() is False:
            fpath_tform_obj.parent.mkdir(parents=True, exist_ok=True)
        torch.save(tform_obj.detach().cpu(), f=fpath_tform_obj)


@dataclass
class OD3D_FrameModalitiesMixin:
    modalities: List


# note these classes can be inherited by frame and sequence classes
@dataclass
class OD3D_CamTform4x4ObjTypeMixin(OD3D_Object):
    cam_tform4x4_obj_type: OD3D_CAM_TFORM_OBJ_TYPES


@dataclass
class OD3D_MaskTypeMixin(OD3D_Object):
    mask_type: OD3D_FRAME_MASK_TYPES


@dataclass
class OD3D_DepthTypeMixin(OD3D_Object):
    depth_type: OD3D_FRAME_DEPTH_TYPES


@dataclass
class OD3D_MeshTypeMixin(OD3D_Object):
    mesh_type: OD3D_MESH_TYPES

    def get_mesh_type_unique(self, mesh_type=None):
        if mesh_type is None:
            mesh_type = self.mesh_type
        return Path("").joinpath(f"{mesh_type}")

    @property
    def mesh_type_unique(self):
        return self.get_mesh_type_unique()

    def get_fpath_mesh(self, mesh_type=None):
        if mesh_type is None:
            mesh_type = self.mesh_type
        if mesh_type == OD3D_MESH_TYPES.META:
            return self.get_fpath_mesh_with_rfpath(self.meta.rfpath_mesh)
        else:
            if "trellis" not in mesh_type and "hunyuan" not in mesh_type:
                return self.path_preprocess.joinpath(
                    "mesh",
                    self.get_mesh_type_unique(mesh_type),
                    self.name_unique,
                    "mesh.ply",
                )
            else:
                return self.path_preprocess.joinpath(
                    "mesh",
                    self.get_mesh_type_unique(mesh_type),
                    self.name_unique,
                    "mesh.glb",
                )

    def get_fpath_mesh_with_rfpath(self, rfpath_mesh):
        return self.path_raw.joinpath(rfpath_mesh)

    @property
    def fpath_mesh(self):
        return self.get_fpath_mesh()

    def read_mesh(self, mesh_type=None, device="cpu"):
        mesh = Meshes.read_from_ply_file(
            fpath=self.get_fpath_mesh(mesh_type=mesh_type),
            device=device,
        )

        if mesh_type is None or mesh_type == self.mesh_type:
            self.mesh = mesh
        return mesh

    def get_mesh(self, mesh_type=None, clone=False, device="cpu"):
        if self.mesh is not None and (mesh_type is None or mesh_type == self.mesh_type):
            mesh = self.mesh
        else:
            mesh = self.read_mesh(
                mesh_type=mesh_type,
                device=device,
            )

        if not clone:
            return mesh
        else:
            return mesh.clone()


@dataclass
class OD3D_MeshFeatsTypeMixin(OD3D_Object):
    mesh_feats_type: OD3D_MESH_FEATS_TYPES
    mesh_feats_dist_reduce_type: OD3D_MESH_FEATS_DIST_REDUCE_TYPES


@dataclass
class OD3D_PCLTypeMixin(OD3D_Object):
    pcl_type: OD3D_PCL_TYPES


@dataclass
class OD3D_SequenceSfMTypeMixin(OD3D_Object):
    sfm_type: OD3D_SEQUENCE_SFM_TYPES  # = OD3D_SEQUENCE_SFM_TYPES.DROID


@dataclass
class OD3D_SubsetMixin(OD3D_Object):
    subset: str
