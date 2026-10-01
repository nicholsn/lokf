---
lokf_version: "0.2"
okf_version: "0.2"
base_iri: https://acme.example/genomics/
context: https://w3id.org/lokf/context.jsonld
title: Acme Genomics
description: A LOKF bundle whose concepts are biolink-model classes.
---
# Acme Genomics

Three concepts: a biolink `Gene` and `Disease`, and a LOKF `Dataset` about
both. `biolink_lokf.yaml`, one level up, is the LOKF domain schema that makes the
biolink classes declared types; `lokf adapt` writes it from biolink-model.
