//SPDX-License-Identifier: CC-BY-NC-ND-4.0
pragma solidity ^0.8.18;

import {Governor} from "../@openzeppelin/contracts/governance/Governor.sol";
import {GovernorVotes} from "../@openzeppelin/contracts/governance/extensions/GovernorVotes.sol";
import {GovernorCountingSimple} from "../@openzeppelin/contracts/governance/extensions/GovernorCountingSimple.sol";
import {IVotes} from "../@openzeppelin/contracts/governance/utils/IVotes.sol";


contract TermFinanceGovernor is GovernorVotes, GovernorCountingSimple {
    
    constructor(IVotes _token) Governor("TermFinanceGovernor") GovernorVotes(_token) {
  
    }
    
    function votingDelay() public view virtual override returns (uint256) {
        return 0;
    }

    function votingPeriod() public view virtual override returns (uint256) {
        return 22 hours;
    }

    function quorumNumerator() public pure returns (uint256) {
        return 1;
    }

    function quorumDenominator() public pure  returns (uint256) {
        return 100;
    }

    function quorumVotes() public view  returns (uint256) {
        return token().getPastTotalSupply(block.timestamp) * quorumNumerator() / quorumDenominator();
    }

    function proposalThreshold() public view virtual override returns (uint256) {
        return 1000e18;
    }

    /**
     * @dev Returns the quorum for a timepoint, in terms of number of votes: `supply * numerator / denominator`.
     */
    function quorum(uint256 timepoint) public view virtual override returns (uint256) {
        return (token().getPastTotalSupply(timepoint) * quorumNumerator()) / quorumDenominator();
    }
}