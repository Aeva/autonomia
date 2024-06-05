let
  nixpkgs = fetchTarball "https://github.com/NixOS/nixpkgs/tarball/nixos-23.11";
  pkgs = import nixpkgs { config = {}; overlays = []; };
in

pkgs.mkShellNoCC {
  packages = with pkgs; [
    (python311.withPackages (subpkgs: with subpkgs; [
        pyusb
        pygame
        pip
        virtualenv
    ]))
  ];

  shellHook = ''
    #source venv/bin/activate
    #pip install pycycling
    #pip install pygame
    #pip install pyusb
  '';
}
