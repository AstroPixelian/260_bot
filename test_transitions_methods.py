#!/usr/bin/env python3
"""
测试transitions方法名
Test transitions method names
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from transitions.extensions.asyncio import AsyncMachine

class TestMachine:
    states = ['state1', 'state2', 'success', 'failed']
    
    def __init__(self):
        self.machine = AsyncMachine(
            model=self,
            states=TestMachine.states,
            initial='state1',
            auto_transitions=False
        )
        
        transitions = [
            ['go_success', 'state1', 'success'],
            ['go_failed', 'state1', 'failed'],
        ]
        
        self.machine.add_transitions(transitions)

def main():
    test = TestMachine()
    print("Available methods:")
    methods = [method for method in dir(test) if not method.startswith('_')]
    for method in sorted(methods):
        print(f"  {method}")

if __name__ == "__main__":
    main()