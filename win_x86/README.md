## 🛠 Installation & Set Up

1. Virtualbox installation
  - Windows: Download from [here](https://www.virtualbox.org/wiki/Downloads)

2. Vagrant installation
  - Windows: Download from [here](https://www.vagrantup.com/downloads)

3. To start next steps you should have downloaded and installed Vagrant and Virtualbox

## 🚀 Building and setting up for environment
Install Vagrant virtual box plugin
  ```sh
  vagrant plugin install virtualbox
  ```
`Goto your hostos folder with vagrant file` Make sure that you have Vagrantfile in this directory
  ```sh
  vagrant up
  vagrant ssh
  ```
  After this step, whenever you want to ssh to your vm goto this folder and execute `vagrant ssh` or `vagrant up && vagrant ssh`
## Other Vagrant commands
- vagrant halt
- vagrant destroy

## References
- [vagrant virtualbox docs](https://www.vagrantup.com/docs/providers/virtualbox)
