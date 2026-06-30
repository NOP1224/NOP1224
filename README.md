<h1 align="center">Hi, I'm Jiandong Jin</h1>

<p align="center">
  Ph.D. Student in Computer Science and Technology  
  <br>
  Anhui University
  <br>
  Research interests: Unaligned RGB-T Tracking, Multimodal Tracking, Image Matching & Registration, Pedestrian Attribute Recognition
</p>

<p align="center">
  <a href="https://github.com/NOP1224">
    <img src="https://komarev.com/ghpvc/?username=NOP1224&label=Profile%20Views&color=0e75b6&style=flat" />
  </a>
  <a href="https://github.com/NOP1224?tab=followers">
    <img src="https://img.shields.io/github/followers/NOP1224?label=Followers&style=flat" />
  </a>
</p>

---

## Research Focus

My research focuses on **multimodal visual perception under spatial misalignment and modality imbalance**.

- **Unaligned RGB-T Tracking**: robust object tracking under RGB/TIR spatial offset, scale variation, and dynamic modality inconsistency.
- **Multimodal Image Alignment**: homography/affine alignment, cross-modal correspondence, deformable sampling, and registration-aware fusion.
- **Pedestrian Attribute Recognition**: open-source PAR framework design, attribute representation learning, and multimodal/person-centric recognition.
- **Efficient Multimodal Tracking**: lightweight fusion, token pruning, dynamic routing, and edge-deployable tracking systems.

---

## Featured Projects

<table>
<tr>
<td width="50%">

### Unaligned RGB-T Tracking

<a href="https://github.com/NOP1224/Unaligned_RGBT_Tracking">
  <img src="https://github-readme-stats.vercel.app/api/pin/?username=NOP1224&repo=Unaligned_RGBT_Tracking&theme=default" />
</a>

**Role / Contribution**

- Lead contributor / maintainer
- Benchmark construction for unaligned RGB-T tracking
- Dataset release, evaluation toolkit, tracking baselines
- Progressive alignment and multimodal fusion methods

**Research Keywords**

`RGB-T Tracking` · `Unaligned Tracking` · `Multimodal Alignment` · `Homography` · `Deformable Attention`

</td>
<td width="50%">

### OpenPAR

<a href="https://github.com/Event-AHU/OpenPAR">
  <img src="https://github-readme-stats.vercel.app/api/pin/?username=Event-AHU&repo=OpenPAR&theme=default" />
</a>

**Role / Contribution**

- Contributor to open-source PAR framework
- Pedestrian attribute recognition research
- Dataset/model/evaluation support
- Attribute-level representation and recognition experiments

**Research Keywords**

`Pedestrian Attribute Recognition` · `OpenPAR` · `PyTorch` · `Human-Centric Vision`

</td>
</tr>
</table>

---

## Project Contribution Dashboard

> The following table summarizes my main contributions to the two representative projects.

| Project | My Role | Main Contributions | Activity Level | Contribution Estimate |
|---|---|---|---|---|
| [Unaligned_RGBT_Tracking](https://github.com/NOP1224/Unaligned_RGBT_Tracking) | Lead contributor / maintainer | Dataset, benchmark, evaluation toolkit, baseline integration, tracking method implementation, README/documentation | High | To be updated by commit/PR statistics |
| [OpenPAR](https://github.com/Event-AHU/OpenPAR) | Contributor | PAR framework support, model/evaluation components, research experiments, documentation | Medium / High | To be updated by commit/PR statistics |

---

## Activity & Maintenance

<p align="center">
  <img src="https://github-readme-stats.vercel.app/api?username=NOP1224&show_icons=true&count_private=true&hide_title=false&theme=default" height="170" />
  <img src="https://github-readme-stats.vercel.app/api/top-langs/?username=NOP1224&layout=compact&theme=default" height="170" />
</p>

<p align="center">
  <img src="https://github-readme-activity-graph.vercel.app/graph?username=NOP1224&theme=github-compact" />
</p>

---

## Selected Research Outputs

### Unaligned RGB-T Tracking

- **MUART244 Benchmark**: a large-scale benchmark for unaligned RGB-T tracking.
- **Progressive Multi-cue Alignment**: progressive center-offset, scale transformation, and global refinement for unaligned multimodal tracking.
- **Unified Evaluation Toolkit**: evaluation support for aligned and unaligned RGB-T tracking settings.

### Pedestrian Attribute Recognition

- **OpenPAR Framework**: PyTorch-based open-source framework for pedestrian attribute recognition.
- **Attribute Recognition Research**: model design and evaluation for pedestrian-centric visual understanding.

---

## Repository Activity Commands

To calculate accurate project-level contribution statistics, I use the following Git commands:

```bash
# Count commits by author
git shortlog -sne --all

# Count my commits in one repository
git log --author="Jiandong Jin" --oneline --all | wc -l

# Count total commits
git rev-list --all --count

# Count added/deleted lines by author
git log --author="Jiandong Jin" --pretty=tformat: --numstat \
  | awk '{ add += $1; del += $2 } END { print "Added:", add, "Deleted:", del }'
