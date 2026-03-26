"""
Social Arb — Core Topology Engine

Domain-agnostic implementation of Chris Camillo's 5-layer cognitive topology.
The core does not know about specific asset classes (stocks, private companies, etc.).
It only knows about signals, mosaics, theses, timing, and positions.

Domains plug in by implementing the Protocol interfaces in protocols.py.
"""

__version__ = "0.2.0"
