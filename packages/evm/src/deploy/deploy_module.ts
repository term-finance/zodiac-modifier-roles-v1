import { DeployFunction } from "hardhat-deploy/types";
import { HardhatRuntimeEnvironment } from "hardhat/types";

const DAO_SAFE = process.env.DAO_SAFE || "0x";

const deploy: DeployFunction = async function (hre: HardhatRuntimeEnvironment) {
  const { deployments, getNamedAccounts } = hre;
  const { deployer } = await getNamedAccounts();
  const { deploy } = deployments;
  const args = [DAO_SAFE, DAO_SAFE, DAO_SAFE];

  const txCheck = await deploy("Permissions", {
    from: deployer,
    log: true,
  });

  await deploy("Roles", {
    from: deployer,
    args,
    log: true,
    // deterministicDeployment: true,
    libraries: {
      Permissions: txCheck.address,
    },
  });
};

deploy.tags = ["roles-modifier"];
export default deploy;
