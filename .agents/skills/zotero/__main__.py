"""Run the installed package or a copied skill directory."""
if __package__:
    from .scripts.cli import main
else:
    from scripts.cli import main

raise SystemExit(main())
