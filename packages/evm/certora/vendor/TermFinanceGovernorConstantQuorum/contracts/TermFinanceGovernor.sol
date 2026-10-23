//SPDX-License-Identifier: CC-BY-NC-ND-4.0
pragma solidity ^0.8.18;

import {Governor} from "../@openzeppelin/contracts/governance/Governor.sol";
import {GovernorVotes} from "../@openzeppelin/contracts/governance/extensions/GovernorVotes.sol";
import {GovernorCountingSimple} from "../@openzeppelin/contracts/governance/extensions/GovernorCountingSimple.sol";
import {IVotes} from "../@openzeppelin/contracts/governance/utils/IVotes.sol";


contract TermFinanceGovernor is GovernorVotes, GovernorCountingSimple {

    uint256 public constant QUORUM = 1_000_000e18;

    constructor(IVotes _token) Governor("TermFinanceGovernor") GovernorVotes(_token) {
  
    }
    
    function votingDelay() public view virtual override returns (uint256) {
        return 0;
    }

    function votingPeriod() public view virtual override returns (uint256) {
        return 22 hours;
    }

    function proposalThreshold() public view virtual override returns (uint256) {
        return 1000e18;
    }

    /**
     * @dev Returns a fixed quorum of 1,000,000 votes, independent of the timepoint and total supply.
     */
    function quorum(uint256) public pure virtual override returns (uint256) {
        return QUORUM;
    }
}